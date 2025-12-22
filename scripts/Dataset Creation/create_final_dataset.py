#!/usr/bin/env python3
"""
Build a unified analysis dataset (2010–2024) with:
  - all base posting fields (from SJMM JSONL)
  - exposure fields (occupation_exposure, industry_exposure, industry_exposure_weighted, etc.)
  - ai_requirement (v7)

Inputs:
  - Base JSONL (.jsonl.bz2) files: Base Dataset/Data/669_SJMM_Data_SUF_v10.0/sjmm_suf_2024_jsonl/
  - Exposure lookup: Results Datasets/sjmm_ai_exposure.jsonl
  - v7 AI requirements: Results Datasets/ai_mentions/results/requirements/v7/ai_job_requirements_all_*_v7.json

Output:
  - Results Datasets/final_analysis_dataset.parquet
"""

from __future__ import annotations

import bz2
import json
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = ROOT / "Base Dataset" / "Data" / "669_SJMM_Data_SUF_v10.0" / "sjmm_suf_2024_jsonl"
EXPOSURE_PATH = ROOT / "Results Datasets" / "sjmm_ai_exposure.jsonl"
V7_DIR = ROOT / "Results Datasets" / "ai_mentions" / "results" / "requirements" / "v7"
V7_AGG_CSV = V7_DIR / "ai_job_requirements_all_years_v7.csv"
OUT_PATH = ROOT / "Results Datasets" / "final_analysis_dataset.parquet"
CROSSWALK_DIR = ROOT / "External datasets" / "Cross-walks"

# Year filter
YEAR_MIN = 2010
YEAR_MAX = 2024


import pandas as pd


def load_crosswalks() -> dict:
    """Load occupation/industry label crosswalks."""
    cross = {}

    # ISCO 1-digit (major)
    isco1_path = CROSSWALK_DIR / "isco_major_code_to_label.csv"
    if isco1_path.exists():
        isco1 = pd.read_csv(isco1_path)
        isco1["isco_major"] = pd.to_numeric(isco1["isco_major"], errors="coerce")
        cross["isco1_map"] = isco1.set_index("isco_major")["label_en"].to_dict()
    else:
        cross["isco1_map"] = {}

    # ISCO 2-digit (submajor)
    isco2_path = CROSSWALK_DIR / "isco_08_submajor_2digit_code_to_label.csv"
    if isco2_path.exists():
        isco2 = pd.read_csv(isco2_path)
        isco2["isco_08_submajor_2d"] = pd.to_numeric(
            isco2["isco_08_submajor_2d"], errors="coerce"
        )
        cross["isco2_map"] = isco2.set_index("isco_08_submajor_2d")["label_en"].to_dict()
    else:
        cross["isco2_map"] = {}

    # NOGA labels (comp_indu_noga)
    noga_path = CROSSWALK_DIR / "comp_indu_noga_to_noga2digit_expanded.csv"
    if noga_path.exists():
        noga = pd.read_csv(noga_path)
        # one label per comp_indu_noga
        noga["comp_indu_noga"] = pd.to_numeric(noga["comp_indu_noga"], errors="coerce")
        noga_map = (
            noga.dropna(subset=["comp_indu_noga"])
            .drop_duplicates(subset=["comp_indu_noga"])
            .set_index("comp_indu_noga")["label_de"]
            .to_dict()
        )
        cross["noga_map"] = noga_map
    else:
        cross["noga_map"] = {}

    return cross


def extract_year(record: Dict[str, Any]) -> int | None:
    """Return posting year if available; try explicit field, else parse from adve_iden_sjob."""
    for key in ("adve_year", "adve_date_year", "year"):
        if key in record and record[key] is not None:
            try:
                return int(record[key])
            except Exception:
                pass
    ad_id = record.get("adve_iden_sjob")
    if isinstance(ad_id, str):
        parts = ad_id.split("-")
        if len(parts) >= 4 and parts[3].isdigit():
            try:
                return int(parts[3])
            except Exception:
                return None
    return None


def load_exposures() -> Dict[str, Dict[str, Any]]:
    """Load exposure lookup keyed by adve_iden_sjob."""
    lookup: Dict[str, Dict[str, Any]] = {}
    with EXPOSURE_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            ad_id = row.get("adve_iden_sjob")
            if not ad_id:
                continue
            lookup[ad_id] = row
    return lookup


def load_ai_requirements() -> Dict[str, str]:
    """Load ai_requirement from aggregated CSV if present, else from all v7 JSON files."""
    ai_map: Dict[str, str] = {}
    if V7_AGG_CSV.exists():
        with V7_AGG_CSV.open() as fh:
            import csv
            reader = csv.DictReader(fh)
            for row in reader:
                ad_id = row.get("id")
                if not ad_id:
                    continue
                label = row.get("ai_requirement")
                if label is None:
                    continue
                ai_map[ad_id] = str(label).capitalize()
    else:
        for path in V7_DIR.glob("ai_job_requirements_all_*_v7.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            for ads in data.values():
                for ad_id, payload in ads.items():
                    label = str(payload.get("ai_requirement", "False")).capitalize()
                    ai_map[ad_id] = label
    if not ai_map:
        print("Warning: no ai_requirement entries loaded; all will be NA.")
    else:
        print(f"Loaded ai_requirement for {len(ai_map):,} ads")
    return ai_map


def lookup_ai_requirement(ad_id: str, ai_map: Dict[str, str]) -> str | None:
    """Return ai requirement, trying exact id then iteratively trimming trailing dash segments."""
    if ad_id in ai_map:
        return ai_map[ad_id]
    parts = ad_id.split("-")
    # iteratively strip trailing segment
    for cut in range(1, min(3, len(parts))):
        trimmed = "-".join(parts[:-cut])
        if trimmed in ai_map:
            return ai_map[trimmed]
    return None


def main() -> None:
    exposures = load_exposures()
    ai_req = load_ai_requirements()
    crosswalks = load_crosswalks()

    rows = []
    for bz2_file in sorted(BASE_DIR.glob("*.jsonl.bz2")):
        with bz2.open(bz2_file, "rt") as fh:
            for line in fh:
                record = json.loads(line)
                year = extract_year(record)
                if year is None or year < YEAR_MIN or year > YEAR_MAX:
                    continue

                ad_id = record.get("adve_iden_sjob")
                if not ad_id:
                    continue

                # Merge exposures
                exp = exposures.get(ad_id, {})
                record["occupation_exposure"] = exp.get("occupation_exposure")
                record["industry_exposure"] = exp.get("industry_exposure")
                record["industry_exposure_weighted"] = exp.get("industry_exposure_weighted")

                # Merge AI requirement
                record["ai_requirement"] = lookup_ai_requirement(ad_id, ai_req)

                # store posting year explicitly
                record["adve_time_year"] = year

                rows.append(record)

    if not rows:
        raise SystemExit("No records found for the specified year range.")

    df = pd.DataFrame(rows).convert_dtypes()

    # Year filter and ensure int
    df = df[(df["adve_time_year"] >= YEAR_MIN) & (df["adve_time_year"] <= YEAR_MAX)].copy()
    df["adve_time_year"] = df["adve_time_year"].astype("Int64")

    # AI requirement as string/categorical; allowed values plus missing
    df["ai_requirement"] = df["ai_requirement"].astype("string")

    # Exposure fields as float
    for col in ["occupation_exposure", "industry_exposure", "industry_exposure_weighted"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derived ISCO grouping codes and labels
    def _isco_str(series: pd.Series) -> pd.Series:
        s = series.astype("string")
        s = s.str.split(".").str[0]
        s = s.str.replace(r"[^0-9]", "", regex=True)
        return s

    isco_clean = _isco_str(df["occu_isco_2008"]) if "occu_isco_2008" in df.columns else pd.Series(dtype="string")
    if not isco_clean.empty:
        df["occu_isco1_code"] = pd.to_numeric(isco_clean.str[:1], errors="coerce").astype("Int64")
        df["occu_isco2_code"] = pd.to_numeric(isco_clean.str[:2], errors="coerce").astype("Int64")
        isco1_map = crosswalks.get("isco1_map", {})
        isco2_map = crosswalks.get("isco2_map", {})
        if isco1_map:
            df["occu_isco1_label"] = df["occu_isco1_code"].map(isco1_map).astype("string")
        if isco2_map:
            df["occu_isco2_label"] = df["occu_isco2_code"].map(isco2_map).astype("string")

    # NOGA label
    if "comp_indu_noga" in df.columns:
        comp_num = pd.to_numeric(df["comp_indu_noga"], errors="coerce")
        df["comp_indu_noga"] = comp_num.astype("Int64")
        noga_map = crosswalks.get("noga_map", {})
        if noga_map:
            df["comp_indu_noga_label"] = comp_num.map(noga_map).astype("string")

    # Special-code clean columns (value < 0 -> NA)
    # Region clean columns (special negative codes -> NA)
    region_special_codes = {-3, -7, -8, -9}
    for region_col in ["loca_regi_kant", "loca_regi_nuts"]:
        if region_col in df.columns:
            clean_col = f"{region_col}_clean"
            tmp = pd.to_numeric(df[region_col], errors="coerce")
            tmp = tmp.mask(tmp.isin(region_special_codes))
            df[clean_col] = tmp

    special_cols = [
        "vaca_posi_mana",
        "vaca_posi_resp",
        "incu_expe_gene",
        "incu_trai_gene",
        "incu_skil_gene",
        "incu_educ_ide1",
        "incu_educ_ide2",
        "incu_educ_typ1",
        "incu_educ_typ2",
        "incu_educ_yrs1",
        "incu_educ_yrs2",
        "incu_educ_yrsm",
    ]
    for col in special_cols:
        if col in df.columns:
            clean_col = f"{col}_clean"
            df[clean_col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[clean_col] < 0, clean_col] = pd.NA

    # Hiring volume helpers
    if "adve_empl_nraw" in df.columns:
        df["adve_empl_nraw_unknown"] = df["adve_empl_nraw"] == 999
        df["adve_empl_nraw_clean"] = pd.to_numeric(df["adve_empl_nraw"], errors="coerce")
        df.loc[df["adve_empl_nraw_clean"] == 999, "adve_empl_nraw_clean"] = pd.NA

    # Force any remaining object columns to pandas StringDtype to avoid Arrow int casting issues
    obj_cols = [c for c in df.columns if df[c].dtype == object]
    if obj_cols:
        df[obj_cols] = df[obj_cols].astype("string")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {len(df):,} rows to {OUT_PATH}")
    print("Columns:", len(df.columns))


if __name__ == "__main__":
    main()
