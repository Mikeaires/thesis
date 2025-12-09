#!/usr/bin/env python3
"""Utility helpers to prepare NAICS exposure data for downstream use."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

import pandas as pd


NAICS_PATTERN = re.compile(r"\b(\d{4})\b")


def _extract_child_naics(title: str) -> List[str]:
    """Return all four-digit NAICS codes referenced inside parentheses."""
    if not isinstance(title, str):
        return []
    matches = []
    for part in re.findall(r"\(([^)]+)\)", title):
        matches.extend(NAICS_PATTERN.findall(part))
    return [code[:4] for code in matches]


def _build_prefix_map(crosswalk_path: Path) -> Dict[str, List[str]]:
    cw = pd.read_csv(crosswalk_path, dtype=str)
    cw["naics_clean"] = (
        cw["2017\nNAICS\nUS  "]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.strip()
    )
    cw = cw[cw["naics_clean"].str.fullmatch(r"\d+")]
    cw = cw[cw["naics_clean"] != "0"]
    cw["prefix3"] = cw["naics_clean"].str[:3]
    cw["child4"] = cw["naics_clean"].str[:4]
    mapping = (
        cw.groupby("prefix3")["child4"]
        .agg(lambda s: sorted(set(code for code in s if len(code) == 4)))
        .to_dict()
    )
    return mapping


def load_clean_naics_exposure(
    excel_path: Path, crosswalk_path: Path
) -> pd.DataFrame:
    """Read the NAICS exposure sheet and expand aggregate rows.

    Rows whose industry title lists specific child NAICS codes in parentheses
    are expanded so that each referenced code receives the exposure score.
    Aggregate rows without explicit child codes remain unchanged.
    """
    prefix_map = _build_prefix_map(crosswalk_path)

    df = pd.read_excel(
        excel_path,
        sheet_name=" General AIIE (4-Digit NAICS)",
        usecols=["NAICS", "Industry Title", "AIIE"],
        dtype=str,
    ).dropna(subset=["NAICS", "AIIE"])

    df["NAICS"] = df["NAICS"].astype(str).str.strip()
    df["AIIE"] = pd.to_numeric(df["AIIE"], errors="coerce")
    df = df.dropna(subset=["AIIE"])

    rows: List[dict] = []
    for _, row in df.iterrows():
        naics = row["NAICS"]
        title = row["Industry Title"]
        exposure = float(row["AIIE"])
        child_codes = _extract_child_naics(title)
        if child_codes:
            for child in sorted(set(child_codes)):
                rows.append({"NAICS": child, "AIIE": exposure, "source_naics": naics})
        else:
            if naics.endswith("0"):
                children = prefix_map.get(naics[:3], [])
                if children:
                    for child in children:
                        rows.append(
                            {"NAICS": child, "AIIE": exposure, "source_naics": naics}
                        )
                    continue
            rows.append({"NAICS": naics, "AIIE": exposure, "source_naics": naics})

    clean_df = pd.DataFrame(rows)
    clean_df["NAICS"] = clean_df["NAICS"].str[:4]
    clean_df = clean_df.drop_duplicates(subset=["NAICS"])
    return clean_df[["NAICS", "AIIE"]]


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[2]
    excel = base / "External datasets" / "indexes" / "General AIOE and AIIE.xlsx"
    crosswalk = base / "External datasets" / "Cross-walks" / "2017_NAICS_to_ISIC_4.csv"
    output = base / "Results Datasets" / "exposures" / "naics_aiie_clean.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    cleaned = load_clean_naics_exposure(excel, crosswalk)
    cleaned.to_csv(output, index=False)
    print(f"Cleaned NAICS exposure saved to {output}")
