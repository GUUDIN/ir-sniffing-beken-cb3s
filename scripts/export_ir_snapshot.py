#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "server" / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
MASTER_CSV = DATA_DIR / "master_ir_codes.csv"
PROFILES_CSV = DATA_DIR / "ir_command_profiles.csv"


def read_csv_safe(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, skipinitialspace=True)
    except pd.errors.EmptyDataError:
        return []
    return df.fillna("").to_dict(orient="records")


def main() -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S")

    payload = {
        "generated_at": now.isoformat(timespec="seconds"),
        "master_total": 0,
        "profiles_total": 0,
        "master_rows": read_csv_safe(MASTER_CSV),
        "profile_rows": read_csv_safe(PROFILES_CSV),
    }
    payload["master_total"] = len(payload["master_rows"])
    payload["profiles_total"] = len(payload["profile_rows"])

    versioned = SNAPSHOT_DIR / f"ir_snapshot_{stamp}.json"
    latest = SNAPSHOT_DIR / "ir_snapshot_latest.json"

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    versioned.write_text(text + "\n", encoding="utf-8")
    latest.write_text(text + "\n", encoding="utf-8")

    print(f"Snapshot salvo: {versioned}")
    print(f"Snapshot latest: {latest}")
    print(f"master_total={payload['master_total']} profiles_total={payload['profiles_total']}")


if __name__ == "__main__":
    main()
