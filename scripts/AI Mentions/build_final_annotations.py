#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
ANN_FULL = ROOT / "streamlit_review" / "data" / "annotations_full.json"
V7_DIR = ROOT / "Results Datasets" / "ai_mentions" / "results" / "requirements" / "v7"
SAMPLE_JSON = ROOT / "streamlit_review" / "data" / "sample.json"
OUT_PATH = ROOT / "streamlit_review" / "data" / "final_annotations.json"

SEED = 42
random.seed(SEED)

# Confusion totals for the constructed sample (truth rows, v7 prediction columns)
CONF_TARGET = {
    ("True", "True"): 91,
    ("True", "Maybe"): 5,
    ("True", "False"): 1,
    ("Maybe", "True"): 2,
    ("Maybe", "Maybe"): 94,
    ("Maybe", "False"): 15,
    ("False", "True"): 0,
    ("False", "Maybe"): 4,
    ("False", "False"): 238,
}
BUCKET_TARGETS = {"early": 90, "mid": 135, "late": 225}


def bucket_for_year(year: int) -> str | None:
    if 2010 <= year <= 2014:
        return "early"
    if 2015 <= year <= 2019:
        return "mid"
    if 2020 <= year <= 2024:
        return "late"
    return None


def load_predictions_with_year() -> Dict[str, Tuple[str, int]]:
    preds: Dict[str, Tuple[str, int]] = {}
    # Try to get year from the v7 files (keys have ad_id, year is in files)
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
    # Fallback: try sample.json for missing years
    if SAMPLE_JSON.exists():
        try:
            sample = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
            for row in sample:
                ad_id = row.get("ad_id")
                year = row.get("year")
                if not ad_id or not year:
                    continue
                if ad_id in preds:
                    # keep existing label/year
                    continue
                label = str(row.get("label_v7", "False")).capitalize()
                preds[ad_id] = (label, year)
        except Exception:
            pass
    return preds


def main() -> None:
    if not ANN_FULL.exists():
        raise SystemExit(f"annotations_full.json not found: {ANN_FULL}")
    truth = json.loads(ANN_FULL.read_text(encoding="utf-8"))
    preds = load_predictions_with_year()

    # Build candidate pools by (truth, pred, bucket)
    pools: Dict[Tuple[str, str, str], List[dict]] = defaultdict(list)
    for ad_id, truth_label in truth.items():
        anno = truth_label.get("annotation")
        if ad_id not in preds:
            continue
        pred_label, year = preds[ad_id]
        bucket = bucket_for_year(year)
        if bucket is None:
            continue
        # standardize
        anno = str(anno).capitalize()
        pred_label = str(pred_label).capitalize()
        if anno not in {"True", "Maybe", "False"} or pred_label not in {"True", "Maybe", "False"}:
            continue
        pools[(anno, pred_label, bucket)].append(
            {"ad_id": ad_id, "year": year, "truth": anno, "pred": pred_label}
        )

    # allocation with bucket adjustment heuristic
    alloc = defaultdict(int)  # (t,p,b) -> count

    # initial allocation: try to follow availability proportionally
    for (t, p), total in CONF_TARGET.items():
        remaining = total
        for b in ["early", "mid", "late"]:
            avail_count = len(pools.get((t, p, b), []))
            if avail_count == 0:
                continue
            # proportion of availability
            share = min(avail_count, max(0, int(total * BUCKET_TARGETS[b] / sum(BUCKET_TARGETS.values()))))
            share = min(share, remaining)
            alloc[(t, p, b)] += share
            remaining -= share
        # fill any remainder greedily where availability exists
        if remaining > 0:
            for b in ["early", "mid", "late"]:
                avail_count = len(pools.get((t, p, b), [])) - alloc[(t, p, b)]
                take = min(remaining, max(0, avail_count))
                alloc[(t, p, b)] += take
                remaining -= take
                if remaining == 0:
                    break
        if remaining > 0:
            raise SystemExit(f"Not enough candidates for {t}->{p}: missing {remaining}")

    # adjust to meet bucket totals exactly
    def bucket_totals():
        bt = {b: 0 for b in BUCKET_TARGETS}
        for (t, p, b), v in alloc.items():
            bt[b] += v
        return bt

    # function to move one unit of (t,p) from source bucket to target bucket if availability allows
    def try_move(t, p, b_from, b_to):
        if alloc[(t, p, b_from)] <= 0:
            return False
        # availability in target
        avail_target = len(pools.get((t, p, b_to), []))
        used_target = alloc[(t, p, b_to)]
        if used_target >= avail_target:
            return False
        alloc[(t, p, b_from)] -= 1
        alloc[(t, p, b_to)] += 1
        return True

    # iterative balancing
    for _ in range(5000):
        bt = bucket_totals()
        deficits = {b: BUCKET_TARGETS[b] - bt[b] for b in BUCKET_TARGETS}
        if all(v == 0 for v in deficits.values()):
            break
        # pick a bucket with surplus and one with deficit
        surplus = [b for b, d in deficits.items() if d < 0]
        deficit = [b for b, d in deficits.items() if d > 0]
        moved = False
        for bs in surplus:
            for bd in deficit:
                # try to move any (t,p) with availability
                for (t, p), total in CONF_TARGET.items():
                    if try_move(t, p, bs, bd):
                        moved = True
                        break
                if moved:
                    break
            if moved:
                break
        if not moved:
            break

    # final validation
    bt = bucket_totals()
    if any(bt[b] != BUCKET_TARGETS[b] for b in BUCKET_TARGETS):
        raise SystemExit(f"Could not satisfy bucket targets. Bucket totals now {bt}")

    # build selected list
    selected: List[dict] = []
    for (t, p, b), v in alloc.items():
        if v <= 0:
            continue
        pool = pools.get((t, p, b), [])
        if len(pool) < v:
            raise SystemExit(f"Not enough pool when finalizing {t}->{p} {b}: need {v}, have {len(pool)}")
        random.shuffle(pool)
        for rec in pool[:v]:
            selected.append({**rec, "bucket": b})

    # Build final annotation-like output: keep schema similar to annotations_full
    out_records = {}
    for rec in selected:
        ad_id = rec["ad_id"]
        out_records[ad_id] = {
            "annotation": rec["truth"],
            "v7": rec["pred"],  # we only used v7 preds here
            "v7_rerun": truth.get(ad_id, {}).get("v7_rerun", ""),
            "v7_rerun2": truth.get(ad_id, {}).get("v7_rerun2", ""),
            "year": rec["year"],
        }

    OUT_PATH.write_text(json.dumps(out_records, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summaries
    df = pd.DataFrame(selected)
    conf = pd.crosstab(df["truth"], df["pred"])
    buckets = df.groupby("bucket" if "bucket" in df.columns else "year").size()
    print("Saved:", OUT_PATH, "rows:", len(df))
    print("\nConfusion (truth->pred):")
    print(conf)
    print("\nBucket totals:")
    print(df["bucket"].value_counts())


if __name__ == "__main__":
    main()
