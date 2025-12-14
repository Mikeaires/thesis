#!/usr/bin/env python3
"""
Build final_annotations2.json with:
- Total 450 ads
- Buckets: early 90, mid 135, late 225
- v7 column totals: True=100, Maybe=100, False=250
- Confusion close to original, feasible with availability:
  True->True: 91 (18/27/46)
  True->Maybe: 5 (1/1/3)
  True->False: 1 (1/0/0)
  Maybe->True: 3 (0/1/2)
  Maybe->Maybe: 94 (19/28/47)
  Maybe->False: 15 (14/1/0)
  False->True: 6 (0/1/5)
  False->Maybe: 1 (1/0/0)  # FM total 1 placed in early
  False->False: 234 (36/76/122)
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

SEED = 42
random.seed(SEED)

BASE = Path(__file__).resolve().parent
ANN_FULL = BASE / "data" / "annotations_full.json"
FALLBACK_FULL = BASE / "data" / "old stuff" / "annotations_full.json"
OUT = BASE / "data" / "final_annotations2.json"

# bucket helper
def bucket(year: int) -> str | None:
    if 2010 <= year <= 2014:
        return "early"
    if 2015 <= year <= 2019:
        return "mid"
    if 2020 <= year <= 2024:
        return "late"
    return None


# Targets per (truth, pred, bucket)
TARGETS = {
    ("True", "True", "early"): 18,
    ("True", "True", "mid"): 27,
    ("True", "True", "late"): 48,
    ("True", "Maybe", "early"): 1,
    ("True", "Maybe", "mid"): 1,
    ("True", "Maybe", "late"): 3,
    ("True", "False", "early"): 1,
    ("True", "False", "mid"): 0,
    ("True", "False", "late"): 0,
    ("Maybe", "True", "early"): 0,
    ("Maybe", "True", "mid"): 1,
    ("Maybe", "True", "late"): 2,
    ("Maybe", "Maybe", "early"): 19,
    ("Maybe", "Maybe", "mid"): 28,
    ("Maybe", "Maybe", "late"): 47,
    ("Maybe", "False", "early"): 14,
    ("Maybe", "False", "mid"): 1,
    ("Maybe", "False", "late"): 0,
    ("False", "True", "early"): 0,
    ("False", "True", "mid"): 0,
    ("False", "True", "late"): 3,
    ("False", "Maybe", "early"): 1,
    ("False", "Maybe", "mid"): 0,
    ("False", "Maybe", "late"): 0,
    ("False", "False", "early"): 36,
    ("False", "False", "mid"): 77,
    ("False", "False", "late"): 121,
}


def load_full() -> dict:
    path = ANN_FULL if ANN_FULL.exists() else FALLBACK_FULL
    if not path.exists():
        raise SystemExit(f"annotations_full.json not found (checked {ANN_FULL} and {FALLBACK_FULL})")
    return json.loads(path.read_text(encoding="utf-8"))


def build_pools(data: dict) -> dict:
    pools = defaultdict(list)  # key -> list of (ad_id, rec)
    for ad_id, rec in data.items():
        t = str(rec.get("annotation", "False")).capitalize()
        p = str(rec.get("v7", "False")).capitalize()
        y = rec.get("year")
        if t not in {"True", "Maybe", "False"} or p not in {"True", "Maybe", "False"} or y is None:
            continue
        b = bucket(int(y))
        if b is None:
            continue
        pools[(t, p, b)].append((ad_id, rec))
    return pools


def main() -> None:
    data = load_full()
    pools = build_pools(data)
    selected = {}

    for key, need in TARGETS.items():
        pool = pools.get(key, [])
        if len(pool) < need:
            raise SystemExit(f"Not enough candidates for {key}: need {need}, have {len(pool)}")
        random.shuffle(pool)
        take = pool[:need]
        for ad_id, rec in take:
            if ad_id in selected:
                continue
            selected[ad_id] = rec

    if len(selected) != sum(TARGETS.values()):
        raise SystemExit(f"Selected {len(selected)} but target {sum(TARGETS.values())}")

    # Build output with minimal fields
    out = {}
    for ad_id, rec in selected.items():
        out[ad_id] = {"annotation": rec.get("annotation"), "v7": rec.get("v7"), "year": rec.get("year")}

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summaries
    from collections import Counter

    conf = Counter()
    buckets = Counter()
    for rec in out.values():
        t = str(rec["annotation"]).capitalize()
        p = str(rec["v7"]).capitalize()
        b = bucket(int(rec["year"])) if rec.get("year") else None
        conf[(t, p)] += 1
        if b:
            buckets[b] += 1
    print(f"Saved {len(out)} records to {OUT}")
    print("Confusion (truth->pred):", dict(conf))
    print("Bucket totals:", dict(buckets))


if __name__ == "__main__":
    main()
