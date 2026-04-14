import json
import os
import re
import threading
from collections import deque
from datetime import datetime
from pathlib import Path

import pandas as pd
import paho.mqtt.client as mqtt
from flask import Flask, jsonify, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "master_ir_codes.csv"
PROFILE_CSV_PATH = BASE_DIR / "data" / "ir_command_profiles.csv"
DEFAULT_COLUMNS = [
    "ID",
    "Protocolo",
    "Hexadecimal",
    "Tamanho",
    "Classe",
    "Assinatura",
    "Fonte",
    "Timestamp",
    "ReplayJSON",
]
PROFILE_COLUMNS = [
    "Assinatura",
    "ProtocoloHint",
    "Hexadecimal",
    "Tamanho",
    "Classe",
    "Count",
    "FirstSeen",
    "LastSeen",
    "Stable",
    "ReplayMode",
    "ReplayJSON",
]

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPICS = [
    topic.strip()
    for topic in os.getenv(
        "MQTT_TOPICS",
        "+/RESULT,stat/+/RESULT,tele/+/RESULT,+/ir/get,+/ir",
    ).split(",")
    if topic.strip()
]
CANONICAL_CAPTURE_TOPIC = os.getenv("CANONICAL_CAPTURE_TOPIC", "ir_sniffer/capture")
PREFER_RESULT_JSON = os.getenv("PREFER_RESULT_JSON", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DROP_NULL_CAPTURES = os.getenv("DROP_NULL_CAPTURES", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "5050"))
APP_DEBUG = os.getenv("APP_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
STABLE_MIN_COUNT = max(int(os.getenv("STABLE_MIN_COUNT", "3")), 2)
MQTT_IRSEND_TOPIC = os.getenv("MQTT_IRSEND_TOPIC", "cmnd/obkCB3S/IRSend")
MQTT_IRSEND_QOS = min(max(int(os.getenv("MQTT_IRSEND_QOS", "0")), 0), 2)
REPLAY_STATUS_TOPIC = os.getenv("REPLAY_STATUS_TOPIC", "ir_sniffer/replay")
REPLAY_REQUIRE_STABLE = os.getenv("REPLAY_REQUIRE_STABLE", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
REPLAY_ALLOW_UNKNOWN = os.getenv("REPLAY_ALLOW_UNKNOWN", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
REPLAY_DEFAULT_REPEATS = max(int(os.getenv("REPLAY_DEFAULT_REPEATS", "1")), 0)
REPLAY_MAX_REPEATS = max(int(os.getenv("REPLAY_MAX_REPEATS", "10")), REPLAY_DEFAULT_REPEATS)
MANUAL_DEFAULT_PROTOCOL = os.getenv("MANUAL_DEFAULT_PROTOCOL", "NEC").strip().upper() or "NEC"
MANUAL_DEFAULT_BITS = max(int(os.getenv("MANUAL_DEFAULT_BITS", "32")), 1)
MANUAL_DEFAULT_DATA = os.getenv("MANUAL_DEFAULT_DATA", "0x20DF10EF").strip() or "0x20DF10EF"
PLAY_CUSTOM_PROTOCOL_OPTIONS = ["NEC", "SAMSUNG", "LG", "RC5", "RC6", "JVC", "PANASONIC"]
PLAY_CUSTOM_BITS_OPTIONS = [12, 15, 16, 20, 24, 28, 32, 36, 40, 48, 56, 64]
MANUAL_SEND_COMPAT_DUAL = os.getenv("MANUAL_SEND_COMPAT_DUAL", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
IRSEND_MAX_BITS = max(int(os.getenv("IRSEND_MAX_BITS", "64")), 1)
IRSEND_BLOCK_AC_PROTOCOLS = os.getenv("IRSEND_BLOCK_AC_PROTOCOLS", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MQTT_MONITOR_MAX_EVENTS = max(int(os.getenv("MQTT_MONITOR_MAX_EVENTS", "400")), 50)

CSV_LOCK = threading.Lock()
MQTT_MONITOR_LOCK = threading.Lock()
MQTT_MONITOR_EVENTS = deque(maxlen=MQTT_MONITOR_MAX_EVENTS)
MQTT_MONITOR_LAST_ID = 0
RAW_TRIPLET_RE = re.compile(r"^\s*([0-9A-Fa-f]+)\s*,\s*(0x[0-9A-Fa-f]+)\s*,\s*(\d+)\s*$")
KV_CAPTURE_RE = re.compile(
    r"protocol(?:o)?\s*[:=]\s*([A-Za-z0-9_\-]+).*?"
    r"(?:hex|hexadecimal|data)\s*[:=]\s*(0x[0-9A-Fa-f]+).*?"
    r"(?:bits?|tamanho)\s*[:=]\s*(\d+)",
    re.IGNORECASE,
)
IR_LEGACY_RE = re.compile(
    r"^IR_([A-Za-z0-9_]+)\s+"
    r"0x([0-9A-Fa-f]+)"
    r"(?:\s+0x([0-9A-Fa-f]+))?"
    r"(?:\s+(\d+))?"
    r"(?:\s+\((\d+)\s+bits\))?\s*$",
    re.IGNORECASE,
)

app = Flask(__name__)


def mqtt_monitor_add(direction: str, topic: str, payload: str, qos: int = 0, retain: bool = False, rc: int = 0) -> None:
    global MQTT_MONITOR_LAST_ID

    with MQTT_MONITOR_LOCK:
        MQTT_MONITOR_LAST_ID += 1
        MQTT_MONITOR_EVENTS.append(
            {
                "id": MQTT_MONITOR_LAST_ID,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "direction": str(direction),
                "topic": str(topic),
                "payload": str(payload),
                "qos": int(qos),
                "retain": bool(retain),
                "rc": int(rc),
            }
        )


def mqtt_publish(topic: str, payload: str, qos: int = 0, retain: bool = False):
    publish_info = mqtt_client.publish(topic, payload, qos=qos, retain=retain)
    mqtt_monitor_add(
        "tx",
        topic,
        payload,
        qos=qos,
        retain=retain,
        rc=getattr(publish_info, "rc", -1),
    )
    return publish_info


def ensure_csv_exists() -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
        CSV_PATH.write_text(",".join(DEFAULT_COLUMNS) + "\n", encoding="utf-8")
    if not PROFILE_CSV_PATH.exists() or PROFILE_CSV_PATH.stat().st_size == 0:
        PROFILE_CSV_PATH.write_text(",".join(PROFILE_COLUMNS) + "\n", encoding="utf-8")


def load_csv() -> pd.DataFrame:
    ensure_csv_exists()
    try:
        df = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False, skipinitialspace=True)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=DEFAULT_COLUMNS)

    for column in DEFAULT_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df


def load_profiles_csv() -> pd.DataFrame:
    ensure_csv_exists()
    try:
        df = pd.read_csv(PROFILE_CSV_PATH, dtype=str, keep_default_na=False, skipinitialspace=True)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=PROFILE_COLUMNS)

    for column in PROFILE_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df


def next_row_id(df: pd.DataFrame) -> int:
    if "ID" not in df.columns or df.empty:
        return 1

    ids = pd.to_numeric(df["ID"], errors="coerce").dropna()
    if ids.empty:
        return 1
    return int(ids.max()) + 1


def normalize_hex(hex_value: str) -> str:
    value = str(hex_value or "").strip()
    if not value:
        return "0x0"

    if ":" in value:
        parts = [normalize_hex(part) for part in value.split(":")]
        return ":".join(parts)

    if value.lower().startswith("0x"):
        body = value[2:].upper() or "0"
        return f"0x{body}"

    if re.fullmatch(r"[0-9A-Fa-f]+", value):
        return f"0x{value.upper()}"

    return value


def is_effectively_zero_hex(hex_value: str) -> bool:
    normalized = normalize_hex(hex_value).strip().lower()
    if not normalized:
        return True

    for part in normalized.split(":"):
        token = part.strip()
        if token.startswith("0x"):
            token = token[2:]
        token = token.lstrip("0")
        if token:
            return False

    return True


def classify_capture(protocol: str, bits: int, hex_value: str) -> str:
    # Some firmwares occasionally report a protocol with Bits=0 while still
    # providing non-zero payload fragments (e.g. "0x0:0x40"). Treat those as
    # unknown rather than noise so they remain visible for diagnostics.
    if bits <= 0:
        return "noise" if is_effectively_zero_hex(hex_value) else "unknown"

    if is_effectively_zero_hex(hex_value):
        return "noise"

    protocol_name = str(protocol).strip().upper()
    if protocol_name == "UNKNOWN" or protocol_name.startswith("PROTO_ID_"):
        return "unknown"
    return "decoded"


def build_signature(bits: int, hex_value: str) -> str:
    return f"{max(bits, 0)}:{normalize_hex(hex_value)}"


def build_replay_json(protocol: str, bits: int, hex_value: str) -> str:
    payload = {
        "Protocol": str(protocol),
        "Bits": max(int(bits), 0),
        "Data": normalize_hex(hex_value),
    }
    return json.dumps(payload, separators=(",", ":"))


def build_irsend_command(protocol: str, bits: int, hex_value: str, repeats: int) -> str:
    protocol_name = (str(protocol).strip() or "UNKNOWN").upper()
    return f"{protocol_name},{max(int(bits), 0)},{normalize_hex(hex_value)},{max(int(repeats), 0)}"


def parse_repeats(value) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return REPLAY_DEFAULT_REPEATS
    return min(max(parsed, 0), REPLAY_MAX_REPEATS)


def is_stable_value(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_bits(value, default: int = MANUAL_DEFAULT_BITS) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, 1), 64)


def validate_protocol_name(value: str) -> str:
    protocol_name = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9_]+", protocol_name):
        return ""
    return protocol_name


def is_ac_protocol_name(protocol_name: str) -> bool:
    name = str(protocol_name or "").strip().upper()
    return name.endswith("_AC") or name.endswith("AC")


def validate_irsend_capability(protocol: str, bits: int):
    protocol_name = (str(protocol) or "").strip().upper()

    # PROTO_ID_* are internal placeholders produced by parsing OpenBeken 'ir' topic
    # payloads. IRSend expects protocol names (e.g., NEC, RC5), not numeric IDs.
    if protocol_name.startswith("PROTO_ID_"):
        return (
            False,
            "IRSend blocked: protocol is a numeric PROTO_ID placeholder; map it to a real protocol name or use another send path",
        )

    if bits > IRSEND_MAX_BITS:
        return (
            False,
            f"IRSend blocked: firmware supports up to {IRSEND_MAX_BITS} bits (got {bits})",
        )

    if IRSEND_BLOCK_AC_PROTOCOLS and is_ac_protocol_name(protocol_name):
        return (
            False,
            "IRSend blocked: AC protocols are not supported by this OpenBeken IRSend path",
        )

    return True, ""


def parse_hex_as_int(hex_value: str):
    try:
        return int(normalize_hex(hex_value), 16)
    except (TypeError, ValueError):
        return None


def build_irsend_legacy_command(protocol: str, bits: int, hex_value: str, repeats: int) -> str | None:
    if bits <= 0 or bits > 64:
        return None

    value = parse_hex_as_int(hex_value)
    if value is None:
        return None

    if bits <= 32:
        address = (value >> 16) & 0xFFFF
        command = value & 0xFFFF
    else:
        # Legacy PROT-ADDR-CMD format cannot represent larger raw states well.
        return None

    return f"{protocol}-{address:X}-{command:X}-{max(int(repeats), 0)}"


def replay_http_response(ok: bool, status: int, message: str, extra=None):
    payload = {"ok": ok, "message": message}
    if extra:
        payload.update(extra)

    wants_json = bool(request.is_json) or "application/json" in request.headers.get("Accept", "")
    if wants_json:
        return jsonify(payload), status

    return redirect(
        url_for(
            "index",
            replay_status="ok" if ok else "error",
            replay_message=message,
            replay_signature=payload.get("signature", ""),
            manual_protocol=payload.get("manual_protocol", ""),
            manual_bits=payload.get("manual_bits", ""),
            manual_hex=payload.get("manual_hex", ""),
            manual_repeats=payload.get("manual_repeats", ""),
        )
    )


def build_manual_form_state(protocol: str, bits: int, hex_value: str, repeats: int) -> dict:
    return {
        "manual_protocol": str(protocol).strip().upper(),
        "manual_bits": max(int(bits), 1),
        "manual_hex": normalize_hex(hex_value),
        "manual_repeats": parse_repeats(repeats),
    }


def upsert_profile(
    profiles_df: pd.DataFrame,
    capture_class: str,
    protocol: str,
    bits: int,
    hex_value: str,
    signature: str,
    timestamp_iso: str,
):
    if capture_class == "noise":
        return profiles_df, None, False

    protocol_hint = str(protocol).strip().upper() or "UNKNOWN"
    replay_mode = "protocol_payload" if capture_class == "decoded" else "binary_mirror_best_effort"
    replay_json = build_replay_json(protocol_hint, bits, hex_value)
    normalized_hex = normalize_hex(hex_value)

    mask = profiles_df["Assinatura"] == signature
    existing_indexes = profiles_df.index[mask]

    if len(existing_indexes) == 0:
        row = {
            "Assinatura": signature,
            "ProtocoloHint": protocol_hint,
            "Hexadecimal": normalized_hex,
            "Tamanho": str(max(bits, 0)),
            "Classe": capture_class,
            "Count": "1",
            "FirstSeen": timestamp_iso,
            "LastSeen": timestamp_iso,
            "Stable": "0",
            "ReplayMode": replay_mode,
            "ReplayJSON": replay_json,
        }
        profiles_df = pd.concat([profiles_df, pd.DataFrame([row])], ignore_index=True)
        return profiles_df, 1, False

    idx = existing_indexes[0]
    current_count = _safe_int(profiles_df.at[idx, "Count"], 0)
    next_count = current_count + 1

    existing_protocol = str(profiles_df.at[idx, "ProtocoloHint"]).strip().upper() or "UNKNOWN"
    if existing_protocol == "UNKNOWN" and protocol_hint != "UNKNOWN":
        profiles_df.at[idx, "ProtocoloHint"] = protocol_hint

    merged_class = "decoded" if capture_class == "decoded" or profiles_df.at[idx, "Classe"] == "decoded" else "unknown"
    merged_replay_mode = "protocol_payload" if merged_class == "decoded" else "binary_mirror_best_effort"
    merged_protocol = str(profiles_df.at[idx, "ProtocoloHint"]).strip().upper() or protocol_hint

    profiles_df.at[idx, "Classe"] = merged_class
    profiles_df.at[idx, "Count"] = str(next_count)
    profiles_df.at[idx, "LastSeen"] = timestamp_iso
    profiles_df.at[idx, "ReplayMode"] = merged_replay_mode
    profiles_df.at[idx, "ReplayJSON"] = build_replay_json(merged_protocol, bits, normalized_hex)

    is_stable = next_count >= STABLE_MIN_COUNT
    profiles_df.at[idx, "Stable"] = "1" if is_stable else "0"
    return profiles_df, next_count, is_stable


def backfill_profiles_from_master() -> int:
    """Rebuild profile table from existing master captures.

    Returns number of profiles generated.
    """
    with CSV_LOCK:
        df = load_csv()
        profiles_df = pd.DataFrame(columns=PROFILE_COLUMNS)

        if df.empty:
            profiles_df.to_csv(PROFILE_CSV_PATH, index=False)
            return 0

        if "ID" in df.columns:
            df["_id_sort"] = pd.to_numeric(df["ID"], errors="coerce")
            df = df.sort_values(by=["_id_sort", "ID"], na_position="last").drop(columns=["_id_sort"])

        for _, row in df.iterrows():
            protocol = str(row.get("Protocolo", "UNKNOWN"))
            bits = _safe_int(row.get("Tamanho"), 0)
            hex_value = normalize_hex(str(row.get("Hexadecimal", "0x0")))
            timestamp_iso = str(row.get("Timestamp", "")) or datetime.now().isoformat(timespec="seconds")

            capture_class = classify_capture(protocol, bits, hex_value)
            signature = build_signature(bits, hex_value)

            profiles_df, _, _ = upsert_profile(
                profiles_df,
                capture_class,
                protocol,
                bits,
                hex_value,
                signature,
                timestamp_iso,
            )

        profiles_df.to_csv(PROFILE_CSV_PATH, index=False)
        return len(profiles_df.index)


def append_capture(protocol: str, hex_value: str, bits: int, source_topic: str):
    timestamp_iso = datetime.now().isoformat(timespec="seconds")
    normalized_hex = normalize_hex(hex_value)
    capture_class = classify_capture(protocol, bits, normalized_hex)
    signature = build_signature(bits, normalized_hex)
    replay_json = build_replay_json(protocol, bits, normalized_hex)

    with CSV_LOCK:
        df = load_csv()
        profiles_df = load_profiles_csv()
        new_id = next_row_id(df)
        row = {
            "ID": str(new_id),
            "Protocolo": protocol,
            "Hexadecimal": normalized_hex,
            "Tamanho": str(bits),
            "Classe": capture_class,
            "Assinatura": signature,
            "Fonte": source_topic,
            "Timestamp": timestamp_iso,
            "ReplayJSON": replay_json,
        }

        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df.to_csv(CSV_PATH, index=False)

        profiles_df, profile_count, profile_stable = upsert_profile(
            profiles_df,
            capture_class,
            protocol,
            bits,
            normalized_hex,
            signature,
            timestamp_iso,
        )
        profiles_df.to_csv(PROFILE_CSV_PATH, index=False)
        return {
            "row_id": new_id,
            "timestamp": timestamp_iso,
            "capture_class": capture_class,
            "signature": signature,
            "replay_json": replay_json,
            "profile_count": profile_count,
            "profile_stable": profile_stable,
        }


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_json_payload(payload: str, require_ir_block: bool = False):
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    ir_block = data.get("IrReceived")
    if isinstance(ir_block, dict):
        protocol = str(ir_block.get("Protocol", "UNKNOWN"))
        bits = _safe_int(ir_block.get("Bits"), 0)
        hex_value = str(ir_block.get("Data", "0x0"))
        return protocol, hex_value, bits

    if require_ir_block:
        return None

    protocol = data.get("Protocol") or data.get("Protocolo")
    bits = data.get("Bits") or data.get("Tamanho")
    hex_value = data.get("Hexadecimal") or data.get("Data")
    if protocol is not None and bits is not None and hex_value is not None:
        return str(protocol), str(hex_value), _safe_int(bits, 0)

    return None


def parse_capture_payload(topic: str, payload: str):
    topic_l = topic.lower().strip()
    is_result_topic = topic_l.endswith("/result")
    is_raw_ir_topic = topic_l.endswith("/ir") or topic_l.endswith("/ir/get")

    # RESULT is the most structured source: prefer it to avoid ambiguous parsing.
    if is_result_topic:
        parsed = _parse_json_payload(payload, require_ir_block=True)
        if parsed:
            return parsed
        return None

    parsed = _parse_json_payload(payload)
    if parsed:
        return parsed

    # Non-IR topics should not be parsed heuristically.
    if not is_raw_ir_topic:
        return None

    raw_match = RAW_TRIPLET_RE.match(payload)
    if raw_match:
        protocol_id, hex_value, bits = raw_match.groups()
        return f"PROTO_ID_{protocol_id.upper()}", hex_value.upper(), _safe_int(bits, 0)

    # OpenBeken IR driver may publish AC states (hasACState) without a Bits field:
    #   "<proto_id_hex>,0x<state...>"
    # In this case, infer Bits from the hex length.
    parts = [part.strip() for part in payload.split(",") if part.strip()]
    if len(parts) == 2 and re.fullmatch(r"[0-9A-Fa-f]+", parts[0]) and parts[1].lower().startswith("0x"):
        protocol_id = parts[0].upper()
        hex_value = parts[1]
        normalized = normalize_hex(hex_value)
        total_hex_digits = 0
        for piece in normalized.split(":"):
            piece = piece.strip()
            if piece.lower().startswith("0x"):
                piece = piece[2:]
            if re.fullmatch(r"[0-9A-Fa-f]+", piece or ""):
                total_hex_digits += len(piece)
            else:
                total_hex_digits = 0
                break
        inferred_bits = total_hex_digits * 4 if total_hex_digits > 0 else 0
        return f"PROTO_ID_{protocol_id}", normalized.upper(), inferred_bits

    kv_match = KV_CAPTURE_RE.search(payload)
    if kv_match:
        protocol, hex_value, bits = kv_match.groups()
        return protocol, hex_value.upper(), _safe_int(bits, 0)

    legacy_match = IR_LEGACY_RE.match(payload)
    if legacy_match:
        protocol, value_a, value_b, _repeat, bits = legacy_match.groups()
        if value_b:
            hex_value = f"0x{value_a.upper()}:0x{value_b.upper()}"
        else:
            hex_value = f"0x{value_a.upper()}"
        return protocol, hex_value, _safe_int(bits, 0)

    if len(parts) >= 3:
        protocol = parts[0]
        hex_value = parts[1]
        bits = _safe_int(parts[2], -1)
        if bits >= 0:
            return protocol, hex_value, bits

    return None


def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties) -> None:
    print(f"Connected to MQTT broker with code: {reason_code}")
    for topic in MQTT_TOPICS:
        client.subscribe(topic)
        print(f"Subscribed to topic: {topic}")


def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
    payload = msg.payload.decode("utf-8", errors="replace").strip()
    if not payload:
        return

    mqtt_monitor_add("rx", msg.topic, payload, qos=msg.qos, retain=bool(msg.retain), rc=0)

    parsed = parse_capture_payload(msg.topic, payload)
    if not parsed:
        print(f"[MQTT] Unrecognized payload format topic={msg.topic} payload={payload}")
        return

    protocol, hex_value, bits = parsed

    # When PREFER_RESULT_JSON=1 we usually ignore the `.../ir` topic because it is
    # less structured/noisier than `.../RESULT`. However, OpenBeken may publish
    # long AC states on `.../ir` using a reduced 2-field format without `Bits`:
    #   "<proto_id_hex>,0x<state...>"
    # Those captures can be missing from RESULT, so we allow them through.
    allow_raw_ir_due_to_ac_state = False
    if msg.topic.lower().endswith("/ir"):
        parts = [part.strip() for part in payload.split(",") if part.strip()]
        if len(parts) == 2 and re.fullmatch(r"[0-9A-Fa-f]+", parts[0]) and parts[1].lower().startswith("0x"):
            allow_raw_ir_due_to_ac_state = True

    # Optional anti-noise gate for frames that are effectively null captures.
    if DROP_NULL_CAPTURES and bits == 0 and is_effectively_zero_hex(hex_value):
        print(
            f"[MQTT] Dropped null capture topic={msg.topic} "
            f"protocol={protocol} hex={hex_value} bits={bits}"
        )
        return

    if PREFER_RESULT_JSON and msg.topic.lower().endswith("/ir") and not allow_raw_ir_due_to_ac_state:
        print(
            f"[MQTT] Ignored raw IR topic due to PREFER_RESULT_JSON=1: "
            f"topic={msg.topic} payload={payload}"
        )
        return

    save_result = append_capture(protocol, hex_value, bits, msg.topic)
    print(
        f"[MQTT] Saved row #{save_result['row_id']} at {save_result['timestamp']}: "
        f"topic={msg.topic} protocol={protocol} hex={hex_value} bits={bits} "
        f"class={save_result['capture_class']} signature={save_result['signature']} "
        f"profile_count={save_result['profile_count']} stable={save_result['profile_stable']}"
    )

    # Re-publish as a normalized capture topic for local integrations.
    normalized_payload = json.dumps(
        {
            "ID": save_result["row_id"],
            "Timestamp": save_result["timestamp"],
            "Protocol": protocol,
            "Hexadecimal": normalize_hex(hex_value),
            "Bits": bits,
            "SourceTopic": msg.topic,
            "Class": save_result["capture_class"],
            "Signature": save_result["signature"],
            "ReplayJSON": save_result["replay_json"],
            "ProfileCount": save_result["profile_count"],
            "Stable": bool(save_result["profile_stable"]),
        }
    )
    mqtt_publish(CANONICAL_CAPTURE_TOPIC, normalized_payload, qos=0, retain=False)


mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message


@app.route("/")
def index():
    with CSV_LOCK:
        df = load_csv()
        profiles_df = load_profiles_csv()

    # Keep timeline style ordering by ID whenever IDs are numeric.
    df["_id_sort"] = pd.to_numeric(df["ID"], errors="coerce")
    df = df.sort_values(by=["_id_sort", "ID"], na_position="last").drop(columns=["_id_sort"])
    rows = df.fillna("").to_dict(orient="records")

    profiles_df["_count_sort"] = pd.to_numeric(profiles_df["Count"], errors="coerce").fillna(0)
    profiles_df = profiles_df.sort_values(by=["_count_sort", "LastSeen"], ascending=[False, False]).drop(
        columns=["_count_sort"]
    )
    profiles = profiles_df.fillna("").to_dict(orient="records")

    replay_feedback = {
        "status": request.args.get("replay_status", "").strip().lower(),
        "message": request.args.get("replay_message", "").strip(),
        "signature": request.args.get("replay_signature", "").strip(),
    }

    requested_manual_protocol = validate_protocol_name(request.args.get("manual_protocol", MANUAL_DEFAULT_PROTOCOL))
    manual_protocol = requested_manual_protocol if requested_manual_protocol in PLAY_CUSTOM_PROTOCOL_OPTIONS else MANUAL_DEFAULT_PROTOCOL

    requested_manual_bits = parse_bits(request.args.get("manual_bits", MANUAL_DEFAULT_BITS))
    manual_bits = requested_manual_bits if requested_manual_bits in PLAY_CUSTOM_BITS_OPTIONS else MANUAL_DEFAULT_BITS

    manual_hex = normalize_hex(request.args.get("manual_hex", MANUAL_DEFAULT_DATA))
    manual_repeats = parse_repeats(request.args.get("manual_repeats", REPLAY_DEFAULT_REPEATS))

    return render_template(
        "index.html",
        rows=rows,
        profiles=profiles,
        stable_min_count=STABLE_MIN_COUNT,
        replay_feedback=replay_feedback,
        replay_allow_unknown=REPLAY_ALLOW_UNKNOWN,
        replay_default_repeats=REPLAY_DEFAULT_REPEATS,
        replay_max_repeats=REPLAY_MAX_REPEATS,
        replay_require_stable=REPLAY_REQUIRE_STABLE,
        replay_topic=MQTT_IRSEND_TOPIC,
        manual_default_protocol=manual_protocol,
        manual_default_bits=manual_bits,
        manual_default_data=manual_hex,
        manual_default_repeats=manual_repeats,
        play_custom_protocol_options=PLAY_CUSTOM_PROTOCOL_OPTIONS,
        play_custom_bits_options=PLAY_CUSTOM_BITS_OPTIONS,
        manual_send_compat_dual=MANUAL_SEND_COMPAT_DUAL,
        irsend_max_bits=IRSEND_MAX_BITS,
        irsend_block_ac_protocols=IRSEND_BLOCK_AC_PROTOCOLS,
    )


@app.route("/profiles")
def profiles_api():
    with CSV_LOCK:
        profiles_df = load_profiles_csv()

    profiles_df["_count_sort"] = pd.to_numeric(profiles_df["Count"], errors="coerce").fillna(0)
    profiles_df = profiles_df.sort_values(by=["_count_sort", "LastSeen"], ascending=[False, False]).drop(
        columns=["_count_sort"]
    )

    profiles = profiles_df.fillna("").to_dict(orient="records")
    stable = [item for item in profiles if str(item.get("Stable", "0")) == "1"]
    return jsonify(
        {
            "stable_min_count": STABLE_MIN_COUNT,
            "replay_require_stable": REPLAY_REQUIRE_STABLE,
            "replay_allow_unknown": REPLAY_ALLOW_UNKNOWN,
            "replay_command_topic": MQTT_IRSEND_TOPIC,
            "total_profiles": len(profiles),
            "stable_profiles": len(stable),
            "profiles": profiles,
        }
    )


@app.route("/monitor/events")
def monitor_events_api():
    after_id = _safe_int(request.args.get("after_id"), 0)
    limit = min(max(_safe_int(request.args.get("limit"), 120), 1), MQTT_MONITOR_MAX_EVENTS)

    with MQTT_MONITOR_LOCK:
        events = [event for event in MQTT_MONITOR_EVENTS if int(event.get("id", 0)) > after_id]
        if len(events) > limit:
            events = events[-limit:]
        last_id = MQTT_MONITOR_LAST_ID

    return jsonify(
        {
            "events": events,
            "last_id": last_id,
            "max_events": MQTT_MONITOR_MAX_EVENTS,
        }
    )


@app.route("/replay", methods=["POST"])
def replay_profile():
    body = request.get_json(silent=True) or {}

    signature = str(body.get("signature") or request.form.get("signature", "")).strip()
    if not signature:
        return replay_http_response(False, 400, "Missing profile signature")

    repeats = parse_repeats(body.get("repeats", request.form.get("repeats")))

    with CSV_LOCK:
        profiles_df = load_profiles_csv()

    match = profiles_df[profiles_df["Assinatura"] == signature]
    if match.empty:
        return replay_http_response(False, 404, f"Profile signature not found: {signature}")

    profile = match.iloc[0].to_dict()
    capture_class = str(profile.get("Classe", "")).strip().lower()
    is_stable = is_stable_value(profile.get("Stable", "0"))

    if capture_class == "noise":
        return replay_http_response(
            False,
            409,
            "Replay blocked: noise profile",
            {"signature": signature},
        )

    if REPLAY_REQUIRE_STABLE and not is_stable:
        return replay_http_response(
            False,
            409,
            "Replay blocked: profile is not stable yet",
            {"signature": signature},
        )

    if capture_class == "unknown" and not REPLAY_ALLOW_UNKNOWN:
        return replay_http_response(
            False,
            409,
            "Replay blocked: unknown profile disabled by policy",
            {"signature": signature},
        )

    protocol = str(profile.get("ProtocoloHint", "UNKNOWN")).strip().upper() or "UNKNOWN"
    bits = _safe_int(profile.get("Tamanho"), 0)
    hex_value = str(profile.get("Hexadecimal", "0x0"))

    capability_ok, capability_msg = validate_irsend_capability(protocol, bits)
    if not capability_ok:
        return replay_http_response(
            False,
            409,
            capability_msg,
            {
                "signature": signature,
                "protocol": protocol,
                "bits": bits,
            },
        )

    command_payload = build_irsend_command(protocol, bits, hex_value, repeats)

    mqtt_info = mqtt_publish(MQTT_IRSEND_TOPIC, command_payload, qos=MQTT_IRSEND_QOS, retain=False)
    mqtt_rc = getattr(mqtt_info, "rc", -1)
    if mqtt_rc != mqtt.MQTT_ERR_SUCCESS:
        return replay_http_response(
            False,
            503,
            f"Replay publish failed (rc={mqtt_rc})",
            {
                "signature": signature,
                "topic": MQTT_IRSEND_TOPIC,
                "payload": command_payload,
            },
        )

    replay_event = {
        "Timestamp": datetime.now().isoformat(timespec="seconds"),
        "Signature": signature,
        "Class": capture_class,
        "Stable": is_stable,
        "Topic": MQTT_IRSEND_TOPIC,
        "Payload": command_payload,
        "Repeats": repeats,
    }
    mqtt_publish(REPLAY_STATUS_TOPIC, json.dumps(replay_event), qos=0, retain=False)

    return replay_http_response(
        True,
        200,
        "Replay command published",
        {
            "signature": signature,
            "topic": MQTT_IRSEND_TOPIC,
            "payload": command_payload,
            "repeats": repeats,
            "stable": is_stable,
            "class": capture_class,
        },
    )


@app.route("/replay/manual", methods=["POST"])
def replay_manual():
    body = request.get_json(silent=True) or {}

    requested_protocol = body.get("protocol", request.form.get("protocol", MANUAL_DEFAULT_PROTOCOL))
    protocol = validate_protocol_name(requested_protocol)

    bits = parse_bits(body.get("bits", request.form.get("bits", MANUAL_DEFAULT_BITS)))
    hex_value = normalize_hex(body.get("hex", request.form.get("hex", MANUAL_DEFAULT_DATA)))
    repeats = parse_repeats(body.get("repeats", request.form.get("repeats", REPLAY_DEFAULT_REPEATS)))

    fallback_protocol = validate_protocol_name(requested_protocol) or MANUAL_DEFAULT_PROTOCOL
    manual_form_state = build_manual_form_state(fallback_protocol, bits, hex_value, repeats)

    if not protocol:
        return replay_http_response(
            False,
            400,
            "Manual replay blocked: invalid protocol name",
            manual_form_state,
        )

    if protocol == "UNKNOWN" and not REPLAY_ALLOW_UNKNOWN:
        return replay_http_response(
            False,
            409,
            "Manual replay blocked: UNKNOWN disabled by policy",
            manual_form_state,
        )

    capability_ok, capability_msg = validate_irsend_capability(protocol, bits)
    if not capability_ok:
        return replay_http_response(
            False,
            409,
            capability_msg,
            {
                "protocol": protocol,
                "bits": bits,
                **manual_form_state,
            },
        )

    signature = f"manual:{protocol}:{bits}:{hex_value}"
    command_payload = build_irsend_command(protocol, bits, hex_value, repeats)
    payloads = [command_payload]

    if MANUAL_SEND_COMPAT_DUAL:
        legacy_payload = build_irsend_legacy_command(protocol, bits, hex_value, repeats)
        if legacy_payload and legacy_payload not in payloads:
            payloads.append(legacy_payload)

    for payload in payloads:
        mqtt_info = mqtt_publish(MQTT_IRSEND_TOPIC, payload, qos=MQTT_IRSEND_QOS, retain=False)
        mqtt_rc = getattr(mqtt_info, "rc", -1)
        if mqtt_rc != mqtt.MQTT_ERR_SUCCESS:
            return replay_http_response(
                False,
                503,
                f"Manual replay publish failed (rc={mqtt_rc})",
                {
                    "signature": signature,
                    "topic": MQTT_IRSEND_TOPIC,
                    "payload": payload,
                    **manual_form_state,
                },
            )

    replay_event = {
        "Timestamp": datetime.now().isoformat(timespec="seconds"),
        "Signature": signature,
        "Class": "manual",
        "Stable": True,
        "Topic": MQTT_IRSEND_TOPIC,
        "Payload": command_payload,
        "PayloadVariants": payloads,
        "Repeats": repeats,
    }
    mqtt_publish(REPLAY_STATUS_TOPIC, json.dumps(replay_event), qos=0, retain=False)

    return replay_http_response(
        True,
        200,
        "Manual replay command published",
        {
            "signature": signature,
            "topic": MQTT_IRSEND_TOPIC,
            "payload": command_payload,
            "payload_variants": payloads,
            "repeats": repeats,
            "stable": True,
            "class": "manual",
            **manual_form_state,
        },
    )


def start_mqtt() -> None:
    mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    mqtt_client.loop_start()


if __name__ == "__main__":
    ensure_csv_exists()
    generated = backfill_profiles_from_master()
    print(f"[BOOT] Profiles backfill completed. profiles={generated}")
    start_mqtt()
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)
