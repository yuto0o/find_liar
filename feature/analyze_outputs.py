"""Analyze `outputs/version_*` directories and export failure cases to CSV.

Usage:
  python -m feature.analyze_outputs
  python feature/analyze_outputs.py
"""

import argparse
import csv
import datetime
import json
from pathlib import Path


def analyze(outputs_root: Path, csv_out: Path, max_raw_len: int = 400):
    rows = []
    if not outputs_root.exists():
        print("No outputs directory found:", outputs_root)
        return
    for d in sorted([p for p in outputs_root.iterdir() if p.is_dir()]):
        meta_path = d / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
        repaired = bool(meta.get("repaired"))
        success = bool(meta.get("success", False))
        if not success or repaired:
            # collect parsed and raw attempts
            parsed = None
            parsed_path = d / "parsed.json"
            if parsed_path.exists():
                try:
                    parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
                except Exception:
                    parsed = None

            raw_files = sorted(
                [p for p in d.iterdir() if p.name.startswith("raw_attempt_")]
            )
            raw_first = (
                raw_files[0].read_text(encoding="utf-8")[:max_raw_len]
                if raw_files
                else ""
            )
            raw_last = (
                raw_files[-1].read_text(encoding="utf-8")[:max_raw_len]
                if raw_files
                else ""
            )

            parsed_edges_count = 0
            explanation = ""
            if parsed and isinstance(parsed, dict):
                parsed_edges_count = (
                    len(parsed.get("edges", []))
                    if isinstance(parsed.get("edges", []), list)
                    else 0
                )
                explanation = parsed.get("explanation", "")

            rows.append(
                {
                    "version": d.name,
                    "timestamp": meta.get("timestamp"),
                    "attempts": meta.get("attempts"),
                    "success": success,
                    "repaired": repaired,
                    "parsed_edges_count": parsed_edges_count,
                    "explanation": explanation,
                    "raw_first": raw_first,
                    "raw_last": raw_last,
                    "version_dir": str(d),
                }
            )

    # write CSV
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    with csv_out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "version",
                "timestamp",
                "attempts",
                "success",
                "repaired",
                "parsed_edges_count",
                "explanation",
                "raw_first",
                "raw_last",
                "version_dir",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote {len(rows)} failure/repaired rows to {csv_out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", default="outputs", help="Outputs root directory")
    parser.add_argument(
        "--csv", default="outputs/failure_cases.csv", help="CSV output path"
    )
    args = parser.parse_args()
    analyze(Path(args.outputs), Path(args.csv))


if __name__ == "__main__":
    main()
