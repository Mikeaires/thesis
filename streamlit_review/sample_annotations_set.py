#!/usr/bin/env python3
"""
Sample 450 postings using ONLY v7 predictions (no manual annotations).
Targets (match final_annotations_test style):
  - Buckets: 2010–2014: 90, 2015–2019: 135, 2020–2024: 225
  - Pred totals: True 100, Maybe 100, False 250
  - Per-pred bucket counts: True 20/30/50, Maybe 20/30/50, False 50/75/125
Output: streamlit_review/data/annotations_set.json with fields {ad_id: {v7, year}}
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent  # streamlit_review/
OUT_PATH = BASE / "data" / "annotations_set.json"
# v7 files live under the repo root (BASE.parent)
V7_DIR = BASE.parent / "Results Datasets" / "ai_mentions" / "results" / "requirements" / "v7"

SEED = 42
random.seed(SEED)

BUCKET_TARGETS = {"early": 90, "mid": 135, "late": 225}
PRED_BUCKET_TARGETS = {
    "True": {"early": 20, "mid": 30, "late": 50},
    "Maybe": {"early": 20, "mid": 30, "late": 50},
    "False": {"early": 50, "mid": 75, "late": 125},
}


def bucket(year: int) -> str | None:
    if 2010 <= year <= 2014:
        return "early"
    if 2015 <= year <= 2019:
        return "mid"
    if 2020 <= year <= 2024:
        return "late"
    return None


def load_v7_predictions() -> dict[str, tuple[str, int]]:
    preds: dict[str, tuple[str, int]] = {}
    for p in V7_DIR.glob("ai_job_requirements_all_*_v7.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for y_str, ads in data.items():
            try:
                year = int(y_str)
            except Exception:
                continue
            for ad_id, payload in ads.items():
                label = str(payload.get("ai_requirement", "False")).capitalize()
                preds[ad_id] = (label, year)
    return preds


def main() -> None:
    preds = load_v7_predictions()

    pools: dict[tuple[str, str], list[dict]] = defaultdict(list)  # (label, bucket) -> list
    for ad_id, (label, year) in preds.items():
        b = bucket(year)
        if b is None:
            continue
        if label not in PRED_BUCKET_TARGETS:
            continue
        pools[(label, b)].append({"ad_id": ad_id, "v7": label, "year": year})

    # availability check
    for label, buckets in PRED_BUCKET_TARGETS.items():
        for b, tgt in buckets.items():
            avail = len(pools.get((label, b), []))
            if avail < tgt:
                raise SystemExit(f"Not enough candidates for {label} in {b}: need {tgt}, have {avail}")

    selected = []
    for label, buckets in PRED_BUCKET_TARGETS.items():
        for b, tgt in buckets.items():
            pool = pools[(label, b)]
            random.shuffle(pool)
            selected.extend(pool[:tgt])

    # build output
    out = {rec["ad_id"]: {"v7": rec["v7"], "year": rec["year"]} for rec in selected}
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # summaries
    pred_counts = Counter(rec["v7"] for rec in selected)
    bucket_counts = Counter(bucket(rec["year"]) for rec in selected)
    print(f"Saved {len(selected)} records to {OUT_PATH}")
    print("Pred counts:", pred_counts)
    print("Bucket counts:", bucket_counts)


if __name__ == "__main__":
    main()
