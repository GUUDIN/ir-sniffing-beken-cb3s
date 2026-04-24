#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from pathlib import Path


IR_LEGACY_RE = re.compile(
    r"^IR_([A-Za-z0-9_]+)\s+"
    r"0x([0-9A-Fa-f]+)"
    r"(?:\s+0x([0-9A-Fa-f]+))?"
    r"(?:\s+(\d+))?"
    r"(?:\s+\((\d+)\s+bits\))?\s*$",
    re.IGNORECASE,
)


def hex_digits(payload: str) -> int:
    total = 0
    for part in str(payload).split(":"):
        token = part.strip()
        if token.lower().startswith("0x"):
            token = token[2:]
        if not token:
            continue
        if re.fullmatch(r"[0-9A-Fa-f]+", token):
            total += len(token)
    return total


def is_zero_hex(payload: str) -> bool:
    for part in str(payload).split(":"):
        token = part.strip()
        if token.lower().startswith("0x"):
            token = token[2:]
        token = token.lstrip("0")
        if token:
            return False
    return True


def parse_line(line: str):
    line = line.strip()
    if not line or " " not in line:
        return None
    topic, payload = line.split(" ", 1)
    payload = payload.strip()

    # JSON RESULT style: {"IrReceived": {...}}
    if payload.startswith("{"):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return {"topic": topic, "payload": payload}
        ir = data.get("IrReceived") if isinstance(data, dict) else None
        if isinstance(ir, dict):
            return {
                "topic": topic,
                "payload": payload,
                "protocol": str(ir.get("Protocol", "UNKNOWN")).upper(),
                "bits": int(ir.get("Bits", 0) or 0),
                "data": str(ir.get("Data", "0x0")),
                "source": "result_json",
            }
        return {"topic": topic, "payload": payload}

    # Legacy IR text style: IR_UNKNOWN 0x0 0
    m = IR_LEGACY_RE.match(payload)
    if m:
        proto, a, b, _repeat, bits = m.groups()
        if b:
            data = f"0x{a}:0x{b}"
        else:
            data = f"0x{a}"
        return {
            "topic": topic,
            "payload": payload,
            "protocol": proto.upper(),
            "bits": int(bits or 0),
            "data": data,
            "source": "legacy_text",
        }

    return {"topic": topic, "payload": payload}


def latest_log(base: Path) -> Path | None:
    logs = sorted(base.glob("ac_capture_live_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def main():
    parser = argparse.ArgumentParser(description="Summarize IR capture log and highlight likely AC frames.")
    parser.add_argument("logfile", nargs="?", help="Path to log file. If omitted, use latest ac_capture_live_*.log")
    args = parser.parse_args()

    if args.logfile:
        log_path = Path(args.logfile)
    else:
        log_path = latest_log(Path("server/data/raw_runs"))

    if not log_path or not log_path.exists():
        raise SystemExit("No capture log found. Start a capture session first.")

    topic_counts = Counter()
    protocol_counts = Counter()
    bits_counts = Counter()
    source_counts = Counter()
    total = 0
    parsed_frames = 0
    null_frames = 0
    long_candidates = []

    for raw in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        event = parse_line(raw)
        if not event:
            continue
        total += 1
        topic_counts[event["topic"]] += 1

        if "protocol" not in event:
            continue

        parsed_frames += 1
        source_counts[event["source"]] += 1
        protocol = event["protocol"]
        bits = int(event["bits"])
        data = event["data"]
        digits = hex_digits(data)

        protocol_counts[protocol] += 1
        bits_counts[bits] += 1

        if bits <= 0 or is_zero_hex(data):
            null_frames += 1

        # Heuristic: AC/stateful frames tend to be larger than classic TV 32-bit payloads.
        if bits > 64 or digits >= 16:
            long_candidates.append((protocol, bits, data, event["topic"]))

    print(f"Log: {log_path}")
    print(f"Total lines: {total}")
    print(f"Parsed IR frames: {parsed_frames}")
    if parsed_frames:
        pct = (null_frames / parsed_frames) * 100.0
        print(f"Null/noise frames: {null_frames} ({pct:.1f}%)")

    print("\nTop topics:")
    for topic, count in topic_counts.most_common(10):
        print(f"  {topic}: {count}")

    print("\nTop protocols:")
    for proto, count in protocol_counts.most_common(10):
        print(f"  {proto}: {count}")

    print("\nBits histogram:")
    for bits, count in sorted(bits_counts.items(), key=lambda x: (x[0], -x[1])):
        print(f"  {bits}: {count}")

    print("\nFrame sources:")
    for src, count in source_counts.items():
        print(f"  {src}: {count}")

    print("\nLikely AC/long candidates (up to 20):")
    if not long_candidates:
        print("  none")
    else:
        for proto, bits, data, topic in long_candidates[:20]:
            print(f"  proto={proto} bits={bits} topic={topic} data={data}")


if __name__ == "__main__":
    main()
