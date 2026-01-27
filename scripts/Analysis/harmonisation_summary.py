#!/usr/bin/env python3
"""Generate before/after harmonisation summaries for occupation and industry variables.

Outputs:
  Results Datasets/analysis/harmonisation_summary/
    - summary_unique_counts.csv
    - transformation_steps.csv
    - top_categories_<level>.csv
    - timeseries_shares_<level>.csv
    - timeseries_discontinuities_<level>.csv
    - largest_reassignments_<mapping>.csv
    - coverage_by_year_<domain>.csv
    - coverage_by_year_<stratum>.csv
    - coverage_overall_<stratum>.csv
    - unmapped_codes_<domain>.csv
    - validation_internal.csv
    - validation_logical_keywords_isco1.csv
    - validation_logical_keywords_isco2.csv
    - validation_logical_public_sector.csv
    - validation_sensitivity_overall.csv
    - validation_sensitivity_by_year.csv
    - validation_discontinuity_flags.csv
    - run_metadata.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "Results Datasets" / "final_analysis_dataset.parquet"
EXP_PATH = ROOT / "Results Datasets" / "sjmm_ai_exposure.jsonl"
GAPS_PATH = ROOT / "Results Datasets" / "exposures" / "exposure_gaps.json"
ISCO_LOOKUP_PATH = ROOT / "Results Datasets" / "exposures" / "isco_aioe.json"
COMP_LOOKUP_PATH = ROOT / "Results Datasets" / "exposures" / "comp_indu_noga_aiie.json"
CROSSWALKS_DIR = ROOT / "External datasets" / "Cross-walks"
ISCO_VALID_PATH = CROSSWALKS_DIR / "ISCO-08 EN Structure and definitions.xlsx"
OUT_DIR = ROOT / "Results Datasets" / "analysis" / "harmonisation_summary"
OUT_DIR.mkdir(parents=True, exist_ok=True)

YEAR_MIN = 2010
YEAR_MAX = 2024
TOP_N = 10
DISCONT_THRESHOLD = 0.05


def _as_str(series: pd.Series, zfill: Optional[int] = None) -> pd.Series:
    s = series.astype("string")
    s = s.str.replace(r"[^0-9A-Za-z]", "", regex=True)
    if zfill:
        s = s.apply(lambda x: x.zfill(zfill) if x is not pd.NA and str(x).isdigit() else x)
    return s


def load_final_dataset() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(DATA_PATH)
    df = pd.read_parquet(DATA_PATH)
    df = df[(df["adve_time_year"] >= YEAR_MIN) & (df["adve_time_year"] <= YEAR_MAX)].copy()
    return df


def load_exposure_lookup() -> pd.DataFrame:
    if not EXP_PATH.exists():
        raise FileNotFoundError(EXP_PATH)
    rows = []
    with EXP_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            rows.append(
                {
                    "adve_iden_sjob": rec.get("adve_iden_sjob"),
                    "occupation_partial_mapping_count": rec.get("occupation_partial_mapping_count"),
                    "industry_contribution_count": rec.get("industry_contribution_count"),
                }
            )
    return pd.DataFrame(rows)


def load_lookup_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_valid_isco_codes() -> set[str]:
    if not ISCO_VALID_PATH.exists():
        return set()
    try:
        df = pd.read_excel(ISCO_VALID_PATH, sheet_name=0, dtype=str)
    except Exception:
        df = pd.read_excel(ISCO_VALID_PATH, dtype=str)
    if "ISCO 08 Code" not in df.columns:
        return set()
    codes = df["ISCO 08 Code"].dropna().astype(str).str.strip()
    # keep 4-digit unit groups (Level==4 if present, else length==4)
    if "Level" in df.columns:
        mask = pd.to_numeric(df["Level"], errors="coerce") == 4
        codes = codes[mask]
    else:
        codes = codes[codes.str.fullmatch(r"\d{4}")]
    return set(codes.str.zfill(4))


def unique_counts(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    def _count(col: str, label: str):
        if col in df.columns:
            out.append({
                "variable": label,
                "column": col,
                "unique_non_missing": df[col].dropna().nunique(),
                "missing": df[col].isna().sum(),
            })

    _count("occu_isco_2008", "ISCO-08 4-digit (raw)")
    _count("occu_isco2_code", "ISCO-08 2-digit (harmonised)")
    _count("occu_isco1_code", "ISCO-08 1-digit (harmonised)")
    _count("comp_indu_noga", "comp_indu_noga (raw)")
    _count("industry_section", "NOGA section (harmonised)")
    return pd.DataFrame(out)


def transformation_steps(df: pd.DataFrame, exp: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    steps = []

    # Occupation steps
    steps.append({
        "domain": "occupation",
        "step": "raw_isco_present",
        "count": int(df["occu_isco_2008"].notna().sum()),
        "share": float(df["occu_isco_2008"].notna().mean()),
        "total": total,
    })
    steps.append({
        "domain": "occupation",
        "step": "occupation_exposure_mapped",
        "count": int(df["occupation_exposure"].notna().sum()),
        "share": float(df["occupation_exposure"].notna().mean()),
        "total": total,
    })
    steps.append({
        "domain": "occupation",
        "step": "occupation_exposure_missing",
        "count": int(df["occupation_exposure"].isna().sum()),
        "share": float(df["occupation_exposure"].isna().mean()),
        "total": total,
    })
    if "occu_isco2_code" in df.columns:
        steps.append({
            "domain": "occupation",
            "step": "isco2_assigned",
            "count": int(df["occu_isco2_code"].notna().sum()),
            "share": float(df["occu_isco2_code"].notna().mean()),
            "total": total,
        })
    if "occu_isco1_code" in df.columns:
        steps.append({
            "domain": "occupation",
            "step": "isco1_assigned",
            "count": int(df["occu_isco1_code"].notna().sum()),
            "share": float(df["occu_isco1_code"].notna().mean()),
            "total": total,
        })

    # Merge exposure-level diagnostics (partial mapping, contribution count)
    if not exp.empty and "adve_iden_sjob" in df.columns:
        merged = df[["adve_iden_sjob"]].merge(exp, on="adve_iden_sjob", how="left")
        partial = merged["occupation_partial_mapping_count"].fillna(0) > 0
        steps.append({
            "domain": "occupation",
            "step": "partial_soc_to_isco_mapping",
            "count": int(partial.sum()),
            "share": float(partial.mean()),
            "total": total,
        })

    # Industry steps
    steps.append({
        "domain": "industry",
        "step": "raw_comp_indu_noga_present",
        "count": int(df["comp_indu_noga"].notna().sum()),
        "share": float(df["comp_indu_noga"].notna().mean()),
        "total": total,
    })
    steps.append({
        "domain": "industry",
        "step": "industry_exposure_mapped",
        "count": int(df["industry_exposure_weighted"].notna().sum()),
        "share": float(df["industry_exposure_weighted"].notna().mean()),
        "total": total,
    })
    steps.append({
        "domain": "industry",
        "step": "industry_exposure_missing",
        "count": int(df["industry_exposure_weighted"].isna().sum()),
        "share": float(df["industry_exposure_weighted"].isna().mean()),
        "total": total,
    })
    if "industry_section" in df.columns:
        steps.append({
            "domain": "industry",
            "step": "industry_section_assigned",
            "count": int(df["industry_section"].notna().sum()),
            "share": float(df["industry_section"].notna().mean()),
            "total": total,
        })
    if "industry_section_exposure_weighted" in df.columns:
        steps.append({
            "domain": "industry",
            "step": "industry_section_exposure_mapped",
            "count": int(df["industry_section_exposure_weighted"].notna().sum()),
            "share": float(df["industry_section_exposure_weighted"].notna().mean()),
            "total": total,
        })

    if not exp.empty and "adve_iden_sjob" in df.columns:
        merged = df[["adve_iden_sjob"]].merge(exp, on="adve_iden_sjob", how="left")
        multi = merged["industry_contribution_count"].fillna(0) > 1
        steps.append({
            "domain": "industry",
            "step": "multi_contribution_mappings",
            "count": int(multi.sum()),
            "share": float(multi.mean()),
            "total": total,
        })

    return pd.DataFrame(steps)


def top_categories(df: pd.DataFrame, col: str, label_col: Optional[str], tag: str) -> pd.DataFrame:
    work = df[[col]].copy()
    work["_label"] = df[label_col] if label_col and label_col in df.columns else pd.NA
    vc = work[col].value_counts(dropna=False)
    total = len(df)
    top = vc.head(TOP_N).reset_index()
    top.columns = ["code", "count"]
    top["share"] = top["count"] / total
    if label_col and label_col in df.columns:
        label_map = (
            pd.concat([df[col], df[label_col]], axis=1)
            .dropna(subset=[col])
            .drop_duplicates(subset=[col])
            .set_index(col)[label_col]
            .to_dict()
        )
        top["label"] = top["code"].map(label_map)
    top["level"] = tag
    return top


def timeseries_shares(df: pd.DataFrame, col: str, label_col: Optional[str], tag: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Determine top categories overall
    top_codes = df[col].value_counts(dropna=True).head(TOP_N).index.tolist()
    top_codes_str = set(pd.Series(top_codes, dtype="string"))
    temp = df[["adve_time_year", col]].copy()
    cat = temp[col].astype("string")
    temp["_cat"] = cat.where(cat.isin(top_codes_str), other="Other")
    shares = (
        temp.groupby(["adve_time_year", "_cat"], observed=True)
        .size()
        .rename("count")
        .reset_index()
    )
    totals = shares.groupby("adve_time_year")["count"].transform("sum")
    shares["share"] = shares["count"] / totals
    shares["level"] = tag

    # Discontinuities: max absolute YoY change per category
    discont_rows = []
    for cat, g in shares.sort_values("adve_time_year").groupby("_cat"):
        g = g.sort_values("adve_time_year")
        yoy = g["share"].diff().abs()
        max_jump = yoy.max()
        max_year = g.loc[yoy.idxmax(), "adve_time_year"] if not yoy.isna().all() else np.nan
        discont_rows.append({
            "level": tag,
            "category": cat,
            "max_abs_yoy_change": max_jump,
            "year_of_max_change": max_year,
        })
    discont = pd.DataFrame(discont_rows).sort_values("max_abs_yoy_change", ascending=False)

    # Attach labels to shares
    if label_col and label_col in df.columns:
        label_map = (
            pd.concat([df[col], df[label_col]], axis=1)
            .dropna(subset=[col])
            .drop_duplicates(subset=[col])
            .set_index(col)[label_col]
            .to_dict()
        )
        label_map_str = {str(k): v for k, v in label_map.items()}
        shares["label"] = shares["_cat"].map(label_map_str)
    return shares, discont


def largest_reassignments(df: pd.DataFrame, source_col: str, target_col: str, tag: str, target_label_col: Optional[str] = None) -> pd.DataFrame:
    temp = df[[source_col, target_col]].dropna()
    pairs = temp.groupby([source_col, target_col]).size().reset_index(name="count")
    pairs = pairs.sort_values("count", ascending=False).head(25)
    pairs["mapping"] = tag
    if target_label_col and target_label_col in df.columns:
        label_map = (
            pd.concat([df[target_col], df[target_label_col]], axis=1)
            .dropna(subset=[target_col])
            .drop_duplicates(subset=[target_col])
            .set_index(target_col)[target_label_col]
            .to_dict()
        )
        pairs["target_label"] = pairs[target_col].map(label_map)
    return pairs


def _coverage_frame(
    df: pd.DataFrame,
    eligible_mask: pd.Series,
    mapped_mask: pd.Series,
    fallback_mask: Optional[pd.Series],
    group_cols: list[str],
    domain: str,
) -> pd.DataFrame:
    work = df.copy()
    work["_eligible"] = eligible_mask
    work["_mapped"] = mapped_mask
    if fallback_mask is None:
        work["_fallback"] = False
    else:
        work["_fallback"] = fallback_mask & ~mapped_mask
    work["_unmapped"] = work["_eligible"] & ~work["_mapped"] & ~work["_fallback"]

    agg = (
        work.groupby(group_cols, dropna=False)
        .agg(
            total=("_eligible", "size"),
            eligible=("_eligible", "sum"),
            mapped_target=("_mapped", "sum"),
            mapped_fallback=("_fallback", "sum"),
            unmapped=("_unmapped", "sum"),
        )
        .reset_index()
    )
    # Shares are conditional on eligible observations
    agg["eligible_share"] = agg["eligible"] / agg["total"]
    denom = agg["eligible"].replace({0: np.nan})
    agg["mapped_target_share_of_eligible"] = agg["mapped_target"] / denom
    agg["mapped_fallback_share_of_eligible"] = agg["mapped_fallback"] / denom
    agg["unmapped_share_of_eligible"] = agg["unmapped"] / denom
    agg["domain"] = domain
    return agg


def build_size_band(df: pd.DataFrame) -> Optional[pd.Series]:
    # Use adve_empl_nrec if available; else fall back to adve_empl_nraw_clean
    if "adve_empl_nrec" in df.columns:
        base = pd.to_numeric(df["adve_empl_nrec"], errors="coerce")
    elif "adve_empl_nraw_clean" in df.columns:
        base = pd.to_numeric(df["adve_empl_nraw_clean"], errors="coerce")
    else:
        return None
    bins = [0, 1, 4, 9, 19, 49, 99, 249, np.inf]
    labels = [
        "1",
        "2-4",
        "5-9",
        "10-19",
        "20-49",
        "50-99",
        "100-249",
        "250+",
    ]
    band = pd.cut(base, bins=bins, labels=labels)
    return band.astype("string")


def coverage_outputs(df: pd.DataFrame) -> None:
    # Occupation exposure coverage (ISCO4 -> exposure)
    occ_eligible = df["occu_isco_2008"].notna()
    occ_mapped = df["occupation_exposure"].notna()
    # No explicit fallback exposure for occupation (aggregated codes exist but no exposure mapping)
    occ_fallback = None

    # Industry exposure coverage (comp_indu_noga -> exposure)
    ind_eligible = df["comp_indu_noga"].notna()
    ind_mapped = df["industry_exposure_weighted"].notna()
    # Fallback exposure at section level (rarely differs, but tracked)
    ind_fallback = df["industry_section_exposure_weighted"].notna() if "industry_section_exposure_weighted" in df.columns else None

    # By year
    occ_by_year = _coverage_frame(
        df, occ_eligible, occ_mapped, occ_fallback, ["adve_time_year"], "occupation"
    )
    ind_by_year = _coverage_frame(
        df, ind_eligible, ind_mapped, ind_fallback, ["adve_time_year"], "industry"
    )
    occ_by_year.to_csv(OUT_DIR / "coverage_by_year_occupation.csv", index=False)
    ind_by_year.to_csv(OUT_DIR / "coverage_by_year_industry.csv", index=False)

    # By year + key strata
    strata = []
    if "occu_isco2_code" in df.columns:
        strata.append(("occ_isco2", ["adve_time_year", "occu_isco2_code"], "occupation"))
        strata.append(("occ_isco1", ["adve_time_year", "occu_isco1_code"], "occupation"))
    if "comp_indu_noga" in df.columns:
        strata.append(("comp_indu_noga", ["adve_time_year", "comp_indu_noga"], "industry"))
    if "industry_section" in df.columns:
        strata.append(("industry_section", ["adve_time_year", "industry_section"], "industry"))
    if "loca_regi_kant_clean" in df.columns:
        strata.append(("region_kant", ["adve_time_year", "loca_regi_kant_clean"], "occupation"))
        strata.append(("region_kant_ind", ["adve_time_year", "loca_regi_kant_clean"], "industry"))
    if "loca_regi_nuts_clean" in df.columns:
        strata.append(("region_nuts", ["adve_time_year", "loca_regi_nuts_clean"], "occupation"))
        strata.append(("region_nuts_ind", ["adve_time_year", "loca_regi_nuts_clean"], "industry"))

    size_band = build_size_band(df)
    if size_band is not None:
        df = df.copy()
        df["firm_size_band"] = size_band
        strata.append(("firm_size", ["adve_time_year", "firm_size_band"], "occupation"))
        strata.append(("firm_size_ind", ["adve_time_year", "firm_size_band"], "industry"))

    for tag, group_cols, domain in strata:
        if domain == "occupation":
            cov = _coverage_frame(df, occ_eligible, occ_mapped, occ_fallback, group_cols, domain)
        else:
            cov = _coverage_frame(df, ind_eligible, ind_mapped, ind_fallback, group_cols, domain)
        cov.to_csv(OUT_DIR / f"coverage_by_year_{tag}.csv", index=False)

    # Overall (no year)
    overall_strata = []
    if "occu_isco2_code" in df.columns:
        overall_strata.append(("occ_isco2", ["occu_isco2_code"], "occupation"))
        overall_strata.append(("occ_isco1", ["occu_isco1_code"], "occupation"))
    if "comp_indu_noga" in df.columns:
        overall_strata.append(("comp_indu_noga", ["comp_indu_noga"], "industry"))
    if "industry_section" in df.columns:
        overall_strata.append(("industry_section", ["industry_section"], "industry"))
    if "loca_regi_kant_clean" in df.columns:
        overall_strata.append(("region_kant", ["loca_regi_kant_clean"], "occupation"))
        overall_strata.append(("region_kant_ind", ["loca_regi_kant_clean"], "industry"))
    if "loca_regi_nuts_clean" in df.columns:
        overall_strata.append(("region_nuts", ["loca_regi_nuts_clean"], "occupation"))
        overall_strata.append(("region_nuts_ind", ["loca_regi_nuts_clean"], "industry"))
    if "firm_size_band" in df.columns:
        overall_strata.append(("firm_size", ["firm_size_band"], "occupation"))
        overall_strata.append(("firm_size_ind", ["firm_size_band"], "industry"))

    for tag, group_cols, domain in overall_strata:
        if domain == "occupation":
            cov = _coverage_frame(df, occ_eligible, occ_mapped, occ_fallback, group_cols, domain)
        else:
            cov = _coverage_frame(df, ind_eligible, ind_mapped, ind_fallback, group_cols, domain)
        cov.to_csv(OUT_DIR / f"coverage_overall_{tag}.csv", index=False)


def unmapped_codes_outputs(df: pd.DataFrame) -> None:
    gaps = load_lookup_json(GAPS_PATH)
    occ_gaps = gaps.get("dataset_gaps", {}).get("occupation_missing_exposure", {})
    ind_gaps = gaps.get("dataset_gaps", {}).get("industry_missing_exposure", {})

    isco_lookup = load_lookup_json(ISCO_LOOKUP_PATH)
    valid_isco = load_valid_isco_codes()
    comp_lookup = load_lookup_json(COMP_LOOKUP_PATH)

    # Occupation unmapped codes (analysis dataset)
    occ_missing = (
        df.loc[df["occupation_exposure"].isna() & df["occu_isco_2008"].notna(), "occu_isco_2008"]
        .value_counts()
        .rename_axis("occu_isco_2008")
        .reset_index(name="count")
    )
    def _occ_class(code: str) -> str:
        code_str = str(int(code)).zfill(4) if pd.notna(code) else ""
        if valid_isco and code_str not in valid_isco:
            return "invalid ISCO-08 (not in official list)"
        if code_str.endswith("00"):
            return "technical (aggregate/placeholder ISCO code)"
        if code_str not in isco_lookup:
            return "technical (no SOC-ISCO crosswalk entry)"
        aioe = isco_lookup.get(code_str, {}).get("aioe")
        if aioe is None:
            return "structural (no SOC exposure for mapped SOCs)"
        return "unknown"

    occ_missing["classification"] = occ_missing["occu_isco_2008"].apply(_occ_class)
    occ_missing["soc_codes_without_exposure"] = occ_missing["occu_isco_2008"].apply(
        lambda x: occ_gaps.get(str(int(x)).zfill(4), {}).get("soc_codes_without_exposure", [])
    )
    occ_missing.to_csv(OUT_DIR / "unmapped_codes_occupation.csv", index=False)

    # Industry unmapped codes (analysis dataset)
    ind_missing = (
        df.loc[df["industry_exposure_weighted"].isna() & df["comp_indu_noga"].notna(), "comp_indu_noga"]
        .value_counts()
        .rename_axis("comp_indu_noga")
        .reset_index(name="count")
    )

    def _ind_class(code: str) -> str:
        code_str = str(int(code)).zfill(2) if pd.notna(code) else ""
        if code_str not in comp_lookup:
            return "technical (no comp_indu_noga exposure entry)"
        aiie = comp_lookup.get(code_str, {}).get("aiie")
        if aiie is None:
            return "structural (no NOGA exposure mapping)"
        return "unknown"

    ind_missing["classification"] = ind_missing["comp_indu_noga"].apply(_ind_class)
    ind_missing["reason"] = ind_missing["comp_indu_noga"].apply(
        lambda x: ind_gaps.get(str(int(x)).zfill(2), {}).get("reason", "")
    )
    ind_missing.to_csv(OUT_DIR / "unmapped_codes_industry.csv", index=False)


def internal_validation_outputs(df: pd.DataFrame) -> None:
    rows = []
    isco_lookup = load_lookup_json(ISCO_LOOKUP_PATH)
    valid_isco = load_valid_isco_codes()
    comp_lookup = load_lookup_json(COMP_LOOKUP_PATH)

    # ISCO formatting and lookup membership
    isco_str = df["occu_isco_2008"].astype("string").str.replace(r"[^0-9]", "", regex=True)
    isco_valid_format = isco_str.str.fullmatch(r"\d{4}")
    rows.append({
        "check": "isco_format_4digit",
        "fail_count": int((~isco_valid_format & isco_str.notna()).sum()),
        "total": int(df["occu_isco_2008"].notna().sum()),
        "examples": ";".join(isco_str[~isco_valid_format & isco_str.notna()].value_counts().head(5).index.astype(str)),
    })
    isco_keys = set(isco_lookup.keys())
    isco_in_lookup = isco_str.where(isco_valid_format).isin(isco_keys)
    rows.append({
        "check": "isco_in_lookup",
        "fail_count": int((isco_valid_format & ~isco_in_lookup).sum()),
        "total": int(isco_valid_format.sum()),
        "examples": ";".join(isco_str[isco_valid_format & ~isco_in_lookup].value_counts().head(5).index.astype(str)),
    })
    if valid_isco:
        isco_in_official = isco_str.where(isco_valid_format).isin(valid_isco)
        rows.append({
            "check": "isco_in_official_list",
            "fail_count": int((isco_valid_format & ~isco_in_official).sum()),
            "total": int(isco_valid_format.sum()),
            "examples": ";".join(isco_str[isco_valid_format & ~isco_in_official].value_counts().head(5).index.astype(str)),
        })

    # comp_indu_noga formatting and lookup membership
    comp_str = df["comp_indu_noga"].astype("string").str.replace(r"[^0-9]", "", regex=True)
    comp_valid_format = comp_str.str.fullmatch(r"\d{1,2}")
    comp_norm = comp_str.where(comp_valid_format).apply(lambda x: x.zfill(2) if x is not pd.NA else x)
    rows.append({
        "check": "comp_indu_noga_format_2digit",
        "fail_count": int((~comp_valid_format & comp_str.notna()).sum()),
        "total": int(df["comp_indu_noga"].notna().sum()),
        "examples": ";".join(comp_str[~comp_valid_format & comp_str.notna()].value_counts().head(5).index.astype(str)),
    })
    comp_keys = set(comp_lookup.keys())
    comp_in_lookup = comp_norm.where(comp_valid_format).isin(comp_keys)
    rows.append({
        "check": "comp_indu_noga_in_lookup",
        "fail_count": int((comp_valid_format & ~comp_in_lookup).sum()),
        "total": int(comp_valid_format.sum()),
        "examples": ";".join(comp_norm[comp_valid_format & ~comp_in_lookup].value_counts().head(5).index.astype(str)),
    })

    # Industry section formatting and allowed codes
    section_str = df["industry_section"].astype("string") if "industry_section" in df.columns else pd.Series(dtype="string")
    section_valid_format = section_str.str.fullmatch(r"[A-Z/]+")
    rows.append({
        "check": "industry_section_format",
        "fail_count": int((~section_valid_format & section_str.notna()).sum()),
        "total": int(section_str.notna().sum()),
        "examples": ";".join(section_str[~section_valid_format & section_str.notna()].value_counts().head(5).index.astype(str)),
    })

    allowed_sections = set()
    crosswalk_path = CROSSWALKS_DIR / "comp_indu_noga_noga2_and_noga_section_crosswalk.csv"
    if crosswalk_path.exists():
        cw = pd.read_csv(crosswalk_path, dtype=str)
        allowed_sections = set(cw["noga_section"].dropna().astype(str).str.strip().str.upper().unique())
    if allowed_sections and "industry_section" in df.columns:
        invalid_section = section_str.notna() & ~section_str.isin(allowed_sections)
        rows.append({
            "check": "industry_section_in_crosswalk",
            "fail_count": int(invalid_section.sum()),
            "total": int(section_str.notna().sum()),
            "examples": ";".join(section_str[invalid_section].value_counts().head(5).index.astype(str)),
        })

    # Mixed revision proxy: ISCO08 should be 4-digit; CH-ISCO-19 (5-digit) should not appear in ISCO08
    rows.append({
        "check": "isco08_not_5digit",
        "fail_count": int(isco_str.str.fullmatch(r"\d{5}").fillna(False).sum()),
        "total": int(df["occu_isco_2008"].notna().sum()),
        "examples": ";".join(isco_str[isco_str.str.fullmatch(r"\d{5}").fillna(False)].value_counts().head(5).index.astype(str)),
    })

    out = pd.DataFrame(rows)
    out["fail_share"] = out["fail_count"] / out["total"].replace({0: np.nan})
    out.to_csv(OUT_DIR / "validation_internal.csv", index=False)


def logical_validation_outputs(df: pd.DataFrame) -> None:
    title = df["occu_titl_adve"].astype("string").str.lower() if "occu_titl_adve" in df.columns else pd.Series(dtype="string")

    isco1_rules = [
        ("manager", ["manager", "director", "head", "chief"], {1}),
        ("engineer", ["engineer"], {2}),
        ("technician", ["technician", "tech."], {3}),
        ("clerk", ["clerk", "secretary"], {4}),
        ("sales", ["sales", "retail", "cashier"], {5}),
        ("farmer", ["farmer", "agricultur"], {6}),
        ("driver_operator", ["driver", "operator"], {8}),
        ("labour", ["laborer", "labourer", "helper"], {9}),
        ("teacher", ["teacher", "professor", "lecturer"], {2}),
    ]

    isco1_rows = []
    if "occu_isco1_code" in df.columns and not title.empty:
        isco1 = pd.to_numeric(df["occu_isco1_code"], errors="coerce")
        for name, kws, expected in isco1_rules:
            pattern = "|".join(kws)
            mask = title.str.contains(pattern, regex=True, na=False)
            total = int(mask.sum())
            if total == 0:
                continue
            match = mask & isco1.isin(expected)
            isco1_rows.append({
                "rule": name,
                "expected_isco1": ",".join(str(x) for x in sorted(expected)),
                "total_hits": total,
                "match_count": int(match.sum()),
                "mismatch_count": int((mask & ~match).sum()),
                "match_share": float(match.sum() / total),
            })
    pd.DataFrame(isco1_rows).to_csv(OUT_DIR / "validation_logical_keywords_isco1.csv", index=False)

    isco2_rules = [
        ("nurse", ["nurse", "midwife"], {22}),
        ("doctor", ["doctor", "physician"], {22}),
        ("software", ["software", "developer", "programmer", "data scientist", "data engineer"], {25}),
        ("accounting", ["accountant", "auditor", "controller"], {24}),
        ("sales", ["sales"], {52}),
        ("teacher", ["teacher", "professor", "lecturer"], {23}),
        ("clerk", ["clerk", "secretary"], {41}),
    ]
    isco2_rows = []
    if "occu_isco2_code" in df.columns and not title.empty:
        isco2 = pd.to_numeric(df["occu_isco2_code"], errors="coerce")
        for name, kws, expected in isco2_rules:
            pattern = "|".join(kws)
            mask = title.str.contains(pattern, regex=True, na=False)
            total = int(mask.sum())
            if total == 0:
                continue
            match = mask & isco2.isin(expected)
            isco2_rows.append({
                "rule": name,
                "expected_isco2": ",".join(str(x) for x in sorted(expected)),
                "total_hits": total,
                "match_count": int(match.sum()),
                "mismatch_count": int((mask & ~match).sum()),
                "match_share": float(match.sum() / total),
            })
    pd.DataFrame(isco2_rows).to_csv(OUT_DIR / "validation_logical_keywords_isco2.csv", index=False)

    # Public sector vs industry section heuristic
    if "comp_sect_publ" in df.columns and "industry_section" in df.columns:
        pub = pd.to_numeric(df["comp_sect_publ"], errors="coerce") == 1
        expected_sections = {"O", "P", "Q"}
        section = df["industry_section"].astype("string")
        total = int(pub.sum())
        match = pub & section.isin(expected_sections)
        out = pd.DataFrame([{
            "expected_sections": ",".join(sorted(expected_sections)),
            "total_public": total,
            "match_count": int(match.sum()),
            "mismatch_count": int((pub & ~match).sum()),
            "match_share": float(match.sum() / total) if total else np.nan,
        }])
        out.to_csv(OUT_DIR / "validation_logical_public_sector.csv", index=False)


def sensitivity_outputs(df: pd.DataFrame, exp: pd.DataFrame) -> None:
    if "adve_iden_sjob" in df.columns and not exp.empty:
        merged = df.merge(exp, on="adve_iden_sjob", how="left")
    else:
        merged = df.copy()
        merged["occupation_partial_mapping_count"] = np.nan
        merged["industry_contribution_count"] = np.nan

    merged["occ_partial"] = merged["occupation_partial_mapping_count"].fillna(0) > 0
    merged["ind_multi"] = merged["industry_contribution_count"].fillna(0) > 1

    scenarios = {
        "base_all": pd.Series(True, index=merged.index),
        "occ_no_partial": ~merged["occ_partial"],
        "ind_single_contrib": ~merged["ind_multi"],
        "occ_no_partial_ind_single": ~(merged["occ_partial"] | merged["ind_multi"]),
    }

    def _safe_mean(series: pd.Series) -> float:
        val = pd.to_numeric(series, errors="coerce").mean()
        return float(val) if pd.notna(val) else np.nan

    rows = []
    for name, mask in scenarios.items():
        sub = merged[mask]
        rows.append({
            "scenario": name,
            "n": int(len(sub)),
            "mean_occ_exposure": _safe_mean(sub["occupation_exposure"]) if "occupation_exposure" in sub.columns else np.nan,
            "mean_ind_exposure_weighted": _safe_mean(sub["industry_exposure_weighted"]) if "industry_exposure_weighted" in sub.columns else np.nan,
            "mean_ind_exposure_unweighted": _safe_mean(sub["industry_exposure"]) if "industry_exposure" in sub.columns else np.nan,
        })
    pd.DataFrame(rows).to_csv(OUT_DIR / "validation_sensitivity_overall.csv", index=False)

    # By year
    by_year_rows = []
    for name, mask in scenarios.items():
        sub = merged[mask].copy()
        if "adve_time_year" not in sub.columns:
            continue
        g = sub.groupby("adve_time_year")
        for year, s in g:
            by_year_rows.append({
                "scenario": name,
                "adve_time_year": int(year),
                "n": int(len(s)),
                "mean_occ_exposure": _safe_mean(s["occupation_exposure"]) if "occupation_exposure" in s.columns else np.nan,
                "mean_ind_exposure_weighted": _safe_mean(s["industry_exposure_weighted"]) if "industry_exposure_weighted" in s.columns else np.nan,
                "mean_ind_exposure_unweighted": _safe_mean(s["industry_exposure"]) if "industry_exposure" in s.columns else np.nan,
            })
    pd.DataFrame(by_year_rows).to_csv(OUT_DIR / "validation_sensitivity_by_year.csv", index=False)


def main() -> None:
    df = load_final_dataset()
    exp = load_exposure_lookup()

    # Unique counts
    uniq = unique_counts(df)
    uniq.to_csv(OUT_DIR / "summary_unique_counts.csv", index=False)

    # Transformation steps
    steps = transformation_steps(df, exp)
    steps.to_csv(OUT_DIR / "transformation_steps.csv", index=False)

    # Top categories for each level
    discont_list = []
    levels = [
        ("occu_isco_2008", None, "isco4"),
        ("occu_isco2_code", "occu_isco2_label", "isco2"),
        ("occu_isco1_code", "occu_isco1_label", "isco1"),
        ("comp_indu_noga", "comp_indu_noga_label", "comp_indu_noga"),
        ("industry_section", "industry_section_label", "noga_section"),
    ]
    for col, label_col, tag in levels:
        if col in df.columns:
            top = top_categories(df, col, label_col, tag)
            top.to_csv(OUT_DIR / f"top_categories_{tag}.csv", index=False)

            shares, discont = timeseries_shares(df, col, label_col, tag)
            shares.to_csv(OUT_DIR / f"timeseries_shares_{tag}.csv", index=False)
            discont.to_csv(OUT_DIR / f"timeseries_discontinuities_{tag}.csv", index=False)
            discont_list.append(discont)

    # Largest reassignments
    reassignments = []
    if "occu_isco_2008" in df.columns and "occu_isco2_code" in df.columns:
        reassignments.append(largest_reassignments(df, "occu_isco_2008", "occu_isco2_code", "isco4_to_isco2", "occu_isco2_label"))
    if "occu_isco2_code" in df.columns and "occu_isco1_code" in df.columns:
        reassignments.append(largest_reassignments(df, "occu_isco2_code", "occu_isco1_code", "isco2_to_isco1", "occu_isco1_label"))
    if "comp_indu_noga" in df.columns and "industry_section" in df.columns:
        reassignments.append(largest_reassignments(df, "comp_indu_noga", "industry_section", "comp_to_section", "industry_section_label"))

    if reassignments:
        pd.concat(reassignments, ignore_index=True).to_csv(
            OUT_DIR / "largest_reassignments.csv", index=False
        )

    # Validation checks
    internal_validation_outputs(df)
    logical_validation_outputs(df)
    sensitivity_outputs(df, exp)

    if discont_list:
        all_discont = pd.concat(discont_list, ignore_index=True)
        flags = all_discont[all_discont["max_abs_yoy_change"] >= DISCONT_THRESHOLD].copy()
        flags.to_csv(OUT_DIR / "validation_discontinuity_flags.csv", index=False)

    # Coverage outputs by year/strata
    coverage_outputs(df)

    # Unmapped codes (with classification)
    unmapped_codes_outputs(df)

    # Metadata
    meta = {
        "rows": int(len(df)),
        "year_min": YEAR_MIN,
        "year_max": YEAR_MAX,
        "top_n": TOP_N,
        "data_path": str(DATA_PATH),
        "exposure_path": str(EXP_PATH),
        "gaps_path": str(GAPS_PATH),
    }
    (OUT_DIR / "run_metadata.json").write_text(json.dumps(meta, indent=2))

    print(f"Wrote harmonisation summary outputs to {OUT_DIR}")


if __name__ == "__main__":
    main()
