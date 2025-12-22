#!/usr/bin/env python3
"""Build AI exposure lookups and job-level enrichment for the SJMM dataset.

The script relies on pandas to wrangle the Excel/CSV inputs provided in the
`Aditional datasets` directory and emits:

  * derived/exposures/isco_aioe.json
  * derived/exposures/noga_aiie.json
  * derived/exposures/exposure_gaps.json
  * derived/sjmm_ai_exposure.jsonl
"""

from __future__ import annotations

import bz2
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from preprocess_naics_exposure import load_clean_naics_exposure

ROOT = Path(__file__).resolve().parents[2]
INDEXES_DIR = ROOT / "External datasets" / "indexes"
CROSSWALKS_DIR = ROOT / "External datasets" / "Cross-walks"
SJMM_JSONL_DIR = (
    ROOT
    / "Base Dataset"
    / "Data"
    / "669_SJMM_Data_SUF_v10.0"
    / "sjmm_suf_2024_jsonl"
)

EXPOSURE_DIR = ROOT / "Results Datasets" / "exposures"
EXPOSURE_DIR.mkdir(parents=True, exist_ok=True)
DERIVED_DATA_PATH = ROOT / "Results Datasets" / "sjmm_ai_exposure.jsonl"


def read_csv_with_keyword(path: Path, keyword: str) -> pd.DataFrame:
    """Read a CSV that may have leading filler rows before the header."""
    raw = pd.read_csv(
        path,
        header=None,
        dtype=str,
        skip_blank_lines=False,
        encoding="utf-8-sig",
    )
    mask = raw.apply(
        lambda row: row.astype(str).str.contains(keyword, na=False).any(), axis=1
    )
    header_idx = mask[mask].index
    if header_idx.empty:
        raise ValueError(f"Could not find header containing '{keyword}' in {path}")
    header_row = header_idx[0]
    header = raw.iloc[header_row].fillna("")
    data = raw.iloc[header_row + 1 :].reset_index(drop=True)
    data.columns = header
    return data.dropna(how="all")


def build_occupation_lookup() -> tuple[pd.DataFrame, Dict[str, list[str]]]:
    """Return a dataframe indexed by ISCO with exposure info (SOC10-based)."""
    soc_exposure = pd.read_excel(
        INDEXES_DIR / "General AIOE and AIIE.xlsx",
        sheet_name="General AIOE (SOC)",
        usecols=["SOC Code", "AIOE"],
        dtype=str,
    ).dropna(subset=["SOC Code", "AIOE"])
    soc_exposure["SOC Code"] = soc_exposure["SOC Code"].str.strip()
    soc_exposure["AIOE"] = pd.to_numeric(soc_exposure["AIOE"], errors="coerce")

    crosswalk = pd.read_csv(
        CROSSWALKS_DIR / "SOC_ISCO_Crosswalk .csv",
        usecols=["2010 SOC Code", "ISCO-08 Code", "part"],
        dtype=str,
    ).dropna(subset=["2010 SOC Code", "ISCO-08 Code"])

    crosswalk["2010 SOC Code"] = crosswalk["2010 SOC Code"].str.strip()
    crosswalk["ISCO-08 Code"] = (
        crosswalk["ISCO-08 Code"].str.replace(".", "", regex=False).str.strip().str.zfill(4)
    )

    merged = crosswalk.merge(
        soc_exposure,
        left_on="2010 SOC Code",
        right_on="SOC Code",
        how="left",
    )

    def summarise(group: pd.DataFrame) -> pd.Series:
        soc_codes = sorted(group["2010 SOC Code"].unique())
        available = group.dropna(subset=["AIOE"])
        matched_soc = sorted(available["2010 SOC Code"].unique())
        missing_soc = sorted(set(soc_codes) - set(matched_soc))
        aioe = float(available["AIOE"].mean()) if not available.empty else np.nan
        return pd.Series(
            {
                "aioe": aioe,
                "soc_codes": soc_codes,
                "matched_soc_codes": matched_soc,
                "missing_soc_codes": missing_soc,
                "partial_mapping_count": int((group["part"] == "*").sum()),
            }
        )

    occupation_df = merged.groupby("ISCO-08 Code").apply(summarise)
    occupation_df.index.name = "ISCO-08 Code"

    occ_missing = {
        isco: codes for isco, codes in occupation_df["missing_soc_codes"].items() if codes
    }

    return occupation_df, occ_missing


def build_industry_lookup() -> tuple[pd.DataFrame, Dict[str, str]]:
    """Return dataframe keyed by NOGA-2 with exposure and contributions."""
    naics_exposure = load_clean_naics_exposure(
        INDEXES_DIR / "General AIOE and AIIE.xlsx",
        CROSSWALKS_DIR / "2017_NAICS_to_ISIC_4.csv",
    )

    naics_isic = pd.read_csv(
        CROSSWALKS_DIR / "2017_NAICS_to_ISIC_4.csv",
        dtype=str,
    )
    naics_isic["naics_clean"] = (
        naics_isic["2017\nNAICS\nUS  "]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.strip()
    )
    naics_isic["isic_clean"] = (
        naics_isic["ISIC 4.0"].astype(str).str.replace(".", "", regex=False).str.strip()
    )
    naics_isic = naics_isic[
        naics_isic["naics_clean"].str.fullmatch(r"\d+")
        & naics_isic["isic_clean"].str.fullmatch(r"\d+")
    ]
    naics_isic["naics4"] = naics_isic["naics_clean"].str[:4]
    naics_isic = naics_isic[["naics4", "isic_clean"]].drop_duplicates()

    matched = naics_exposure.merge(
        naics_isic,
        left_on="NAICS",
        right_on="naics4",
        how="left",
    )

    naics_gaps: Dict[str, str] = {}
    no_isic = matched[matched["isic_clean"].isna()]["NAICS"].unique()
    for code in sorted(no_isic):
        naics_gaps[code] = "no ISIC match"

    matched = matched.dropna(subset=["isic_clean"]).copy()
    if matched.empty:
        return pd.DataFrame(), naics_gaps

    matched["isic_clean"] = (
        matched["isic_clean"].astype(str).str.replace(".", "", regex=False).str.strip()
    )
    matched = matched.drop_duplicates(subset=["NAICS", "isic_clean"])

    isic_nace = pd.read_csv(
        CROSSWALKS_DIR / "ISIC4_NACE2.csv",
        usecols=["ISIC4code", "NACE2code"],
        dtype=str,
    ).dropna(subset=["ISIC4code", "NACE2code"])
    isic_nace["isic_clean"] = (
        isic_nace["ISIC4code"].str.replace(".", "", regex=False).str.strip()
    )
    isic_nace["noga_2"] = (
        isic_nace["NACE2code"].str.split(".").str[0].str.strip().str.upper()
    )
    mask_numeric = isic_nace["noga_2"].str.fullmatch(r"\d+")
    isic_nace.loc[mask_numeric, "noga_2"] = (
        isic_nace.loc[mask_numeric, "noga_2"].str.zfill(2)
    )

    merged = matched.merge(
        isic_nace[["isic_clean", "noga_2"]].drop_duplicates(),
        on="isic_clean",
        how="left",
    )

    naics_with_noga = set(merged[merged["noga_2"].notna()]["NAICS"].unique())
    naics_without_noga = sorted(set(matched["NAICS"]) - naics_with_noga)
    for code in naics_without_noga:
        naics_gaps.setdefault(code, "no NOGA match")

    merged = merged[merged["noga_2"].notna()].copy()
    if merged.empty:
        return pd.DataFrame(), naics_gaps

    merged = merged.drop_duplicates(subset=["NAICS", "isic_clean", "noga_2"])

    contributions = (
        merged.groupby(["noga_2", "NAICS"])
        .agg(
            aiie=("AIIE", "first"),
            isic_codes=("isic_clean", lambda s: sorted(set(s))),
            isic_count=("isic_clean", lambda s: len(set(s))),
        )
        .reset_index()
    )

    mean_naics = contributions.groupby("noga_2")["aiie"].mean()
    weighted = contributions.groupby("noga_2").apply(
        lambda df: (df["aiie"] * df["isic_count"]).sum() / df["isic_count"].sum()
    )
    noga_aiie = pd.concat(
        [mean_naics.rename("aiie"), weighted.rename("aiie_weighted")], axis=1
    )
    noga_aiie["aiie"] = noga_aiie["aiie"].astype(float)
    noga_aiie["aiie_weighted"] = noga_aiie["aiie_weighted"].astype(float)

    noga_aiie["contributions"] = contributions.groupby("noga_2").apply(
        lambda df: [
            {
                "naics": row.NAICS,
                "aiie": float(row.aiie),
                "isic_codes": row.isic_codes,
                "isic_count": int(row.isic_count),
            }
            for row in df.itertuples(index=False)
        ],
    )
    noga_aiie["naics_codes"] = noga_aiie["contributions"].apply(
        lambda lst: sorted({item["naics"] for item in lst})
    )
    noga_aiie["isic_codes"] = noga_aiie["contributions"].apply(
        lambda lst: sorted({code for item in lst for code in item["isic_codes"]})
    )

    return noga_aiie, naics_gaps


def write_mapping_files(
    occupation_df: pd.DataFrame,
    industry_df: pd.DataFrame,
    comp_indu_df: pd.DataFrame,
) -> tuple[dict, dict]:
    occ_payload = {}
    for isco, row in occupation_df.iterrows():
        aioe = row["aioe"]
        occ_payload[isco] = {
            "aioe": None if pd.isna(aioe) else float(aioe),
            "soc_codes": row["soc_codes"],
            "matched_soc_codes": row["matched_soc_codes"],
            "partial_mapping_count": int(row["partial_mapping_count"]),
        }

    industry_payload = {}
    for noga, row in industry_df.iterrows():
        aiie = row["aiie"]
        aiie_weighted = row["aiie_weighted"]
        contrib_list = row["contributions"]
        naics_codes = sorted({item["naics"] for item in contrib_list})
        isic_codes = sorted({code for item in contrib_list for code in item["isic_codes"]})
        industry_payload[noga] = {
            "aiie": None if pd.isna(aiie) else float(aiie),
            "aiie_weighted": None if pd.isna(aiie_weighted) else float(aiie_weighted),
            "contributions": contrib_list,
            "naics_codes": naics_codes,
            "isic_codes": isic_codes,
        }

    (EXPOSURE_DIR / "isco_aioe.json").write_text(
        json.dumps(occ_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    (EXPOSURE_DIR / "noga_aiie.json").write_text(
        json.dumps(industry_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    comp_payload = {}
    for comp_code, row in comp_indu_df.iterrows():
        aiie = row["aiie"]
        aiie_weighted = row["aiie_weighted"]
        contrib_list = row["contributions"]
        naics_codes = sorted({item["naics"] for item in contrib_list})
        isic_codes = sorted({code for item in contrib_list for code in item["isic_codes"]})
        comp_payload[comp_code] = {
            "aiie": None if pd.isna(aiie) else float(aiie),
            "aiie_weighted": None if pd.isna(aiie_weighted) else float(aiie_weighted),
            "contributions": contrib_list,
            "naics_codes": naics_codes,
            "isic_codes": isic_codes,
        }
    (EXPOSURE_DIR / "comp_indu_noga_aiie.json").write_text(
        json.dumps(comp_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return occ_payload, industry_payload, comp_payload


def collapse_noga_to_comp(
    industry_df: pd.DataFrame,
) -> pd.DataFrame:
    """Collapse NOGA-2 exposure to SJMM comp_indu_noga groups using the same weighting logic."""
    crosswalk = pd.read_csv(
        CROSSWALKS_DIR / "comp_indu_noga_to_noga2digit_expanded.csv",
        dtype=str,
    )
    crosswalk["comp_indu_noga"] = pd.to_numeric(
        crosswalk["comp_indu_noga"], errors="coerce"
    )
    crosswalk = crosswalk.dropna(subset=["comp_indu_noga", "noga_2digit"]).copy()
    crosswalk["comp_code"] = crosswalk["comp_indu_noga"].astype(int).apply(lambda x: f"{x:02d}")
    crosswalk["noga_2digit"] = (
        crosswalk["noga_2digit"].astype(str).str.strip().str.zfill(2)
    )

    comp_groups = (
        crosswalk.groupby("comp_code")["noga_2digit"]
        .apply(lambda s: sorted(set(s)))
        .to_dict()
    )

    rows = []
    for comp_code, noga_list in comp_groups.items():
        pooled = []
        for noga in noga_list:
            if noga in industry_df.index:
                pooled.extend(industry_df.loc[noga, "contributions"])
        if not pooled:
            rows.append(
                {
                    "comp_indu_noga": comp_code,
                    "aiie": np.nan,
                    "aiie_weighted": np.nan,
                    "contributions": [],
                }
            )
            continue
        aiies = [item["aiie"] for item in pooled]
        weights = [item["isic_count"] for item in pooled]
        aiie = float(np.mean(aiies)) if aiies else np.nan
        aiie_weighted = (
            float(np.average(aiies, weights=weights)) if aiies else np.nan
        )
        rows.append(
            {
                "comp_indu_noga": comp_code,
                "aiie": aiie,
                "aiie_weighted": aiie_weighted,
                "contributions": pooled,
            }
        )

    comp_df = pd.DataFrame(rows).set_index("comp_indu_noga")
    return comp_df


def enrich_job_ads(
    occupation_lookup: dict,
    industry_lookup: dict,
    comp_indu_lookup: dict,
) -> tuple[Dict[str, int], Dict[str, dict], Dict[str, dict]]:
    stats = {
        "total_ads": 0,
        "occupation_exposure_attached": 0,
        "occupation_missing": 0,
        "industry_exposure_attached": 0,
        "industry_missing": 0,
    }
    occ_dataset_gaps: defaultdict[str, dict] = defaultdict(dict)
    ind_dataset_gaps: defaultdict[str, dict] = defaultdict(dict)

    with DERIVED_DATA_PATH.open("w", encoding="utf-8") as out_fh:
        for bz2_file in sorted(SJMM_JSONL_DIR.glob("*.jsonl.bz2")):
            with bz2.open(bz2_file, "rt") as fh:
                for line in fh:
                    record = json.loads(line)
                    stats["total_ads"] += 1

                    isco_raw = record.get("occu_isco_2008")
                    if isinstance(isco_raw, int):
                        isco_code = f"{isco_raw:04d}" if isco_raw >= 0 else None
                    elif (
                        isinstance(isco_raw, str)
                        and isco_raw.strip().isdigit()
                        and int(isco_raw) >= 0
                    ):
                        isco_code = f"{int(isco_raw):04d}"
                    else:
                        isco_code = None

                    occ_entry = occupation_lookup.get(isco_code)
                    if occ_entry and occ_entry.get("aioe") is not None:
                        stats["occupation_exposure_attached"] += 1
                        occ_exposure = occ_entry["aioe"]
                        occ_matched = len(occ_entry.get("matched_soc_codes", []))
                        occ_partial = occ_entry.get("partial_mapping_count", 0)
                        occ_soc_codes = occ_entry.get("soc_codes", [])
                    else:
                        stats["occupation_missing"] += 1
                        occ_exposure = None
                        occ_matched = 0
                        occ_partial = 0
                        occ_soc_codes = occ_entry.get("soc_codes", []) if occ_entry else []
                        gap_key = isco_code or "__missing__"
                        gap_entry = occ_dataset_gaps.setdefault(
                            gap_key,
                            {
                                "count": 0,
                                "soc_codes_without_exposure": occ_soc_codes,
                            },
                        )
                        gap_entry["count"] += 1

                    noga_raw = record.get("comp_indu_noga")
                    if isinstance(noga_raw, int) and noga_raw >= 0:
                        noga_code = f"{noga_raw:02d}"
                    elif isinstance(noga_raw, str) and noga_raw.strip().isdigit():
                        noga_code = str(int(noga_raw)).zfill(2)
                    else:
                        noga_code = None

                    comp_entry = comp_indu_lookup.get(noga_code)
                    ind_entry = comp_entry
                    if ind_entry and ind_entry.get("aiie") is not None:
                        stats["industry_exposure_attached"] += 1
                        ind_exposure = ind_entry["aiie"]
                        ind_exposure_weighted = ind_entry.get("aiie_weighted")
                        contributions = ind_entry.get("contributions", [])
                        ind_contribs = len(contributions)
                        source_naics = ind_entry.get("naics_codes", [])
                        source_isic = ind_entry.get("isic_codes", [])
                    else:
                        stats["industry_missing"] += 1
                        ind_exposure = None
                        ind_exposure_weighted = None
                        ind_contribs = 0
                        source_naics = []
                        source_isic = []
                        gap_key = noga_code or "__missing__"
                        gap_entry = ind_dataset_gaps.setdefault(
                            gap_key,
                            {
                                "count": 0,
                                "reason": "",
                            },
                        )
                        gap_entry["count"] += 1
                        if not gap_entry["reason"]:
                            gap_entry["reason"] = (
                                "dataset record missing NOGA code"
                                if noga_code is None
                                else "comp_indu_noga not present in exposure lookup (collapsed NOGA mapping)"
                            )

                    enriched = {
                        "adve_iden_sjob": record.get("adve_iden_sjob"),
                        "occu_isco_2008": isco_code,
                        "comp_indu_noga": noga_code,
                        "occupation_exposure": occ_exposure,
                        "occupation_matched_soc_count": occ_matched,
                        "occupation_partial_mapping_count": occ_partial,
                        "occupation_source_soc_codes": occ_soc_codes,
                        "industry_exposure_weighted": ind_exposure_weighted,
                        "industry_exposure": ind_exposure,
                        "industry_contribution_count": ind_contribs,
                        "industry_source_naics": source_naics,
                        "industry_source_isic": source_isic,
                    }
                    out_fh.write(json.dumps(enriched) + "\n")

    return stats, dict(occ_dataset_gaps), dict(ind_dataset_gaps)


def main() -> None:
    print("Building occupation exposure lookup (pandas)...")
    occupation_df, occ_missing = build_occupation_lookup()
    print(f"  ISCO codes covered: {occupation_df.shape[0]}")

    print("Building industry exposure lookup (pandas)...")
    industry_df, naics_gaps = build_industry_lookup()
    print(f"  NOGA sections covered: {industry_df.shape[0]}")

    print("Collapsing NOGA exposure to comp_indu_noga groups...")
    comp_indu_df = collapse_noga_to_comp(industry_df)
    print(f"  comp_indu_noga groups covered: {comp_indu_df.shape[0]}")

    print("Writing mapping JSON assets...")
    occupation_lookup, industry_lookup, comp_indu_lookup = write_mapping_files(
        occupation_df,
        industry_df,
        comp_indu_df,
    )

    print("Creating job-level enrichment file...")
    stats, occ_dataset_gaps, ind_dataset_gaps = enrich_job_ads(
        occupation_lookup, industry_lookup, comp_indu_lookup
    )
    gap_payload = {
        "lookup_gaps": {
            "occupation_soc_missing_exposure": occ_missing,
            "industry_naics_crosswalk_gaps": naics_gaps,
        },
        "dataset_gaps": {
            "occupation_missing_exposure": occ_dataset_gaps,
            "industry_missing_exposure": ind_dataset_gaps,
        },
    }
    (EXPOSURE_DIR / "exposure_gaps.json").write_text(
        json.dumps(gap_payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
