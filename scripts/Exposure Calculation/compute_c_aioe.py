#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
IDX_DIR = ROOT / "External datasets" / "indexes"
OUT_XLSX = IDX_DIR / "General C_AIOE.xlsx"
OUT_CSV = IDX_DIR / "General C_AIOE.csv"

# Work context element names present in the provided O*NET download (Scale CX)
WC_RENAME: Dict[str, str] = {
    # Communication
    "Face-to-Face Discussions with Individuals and Within Teams": "face_to_face",
    "Public Speaking": "public_speaking",
    # Responsibility
    "Impact of Decisions on Co-workers or Company Results": "impact_decisions",
    "Health and Safety of Other Workers": "health_safety",
    # Physical
    "Outdoors, Exposed to All Weather Conditions": "outdoors_weather",
    "Physical Proximity": "physical_proximity",
    # Criticality
    "Consequence of Error": "consequence_error",
    "Freedom to Make Decisions": "freedom_decisions",
    "Frequency of Decision Making": "frequency_decisions",
    # Routine
    "Degree of Automation": "degree_automation",
    # Note: structured vs unstructured work is not present in this download
}
WC_ELEMENTS: List[str] = list(WC_RENAME.keys())


def clean_soc(val) -> str:
    """Convert SOC code to 6-digit with dash, drop decimals."""
    s = str(val).strip()
    if "." in s:
        s = s.split(".", 1)[0]
    return s


def load_aioe() -> pd.DataFrame:
    path = IDX_DIR / "General AIOE and AIIE.xlsx"
    xl = pd.ExcelFile(path)
    df = xl.parse("General AIOE (SOC)")
    df["soc6"] = df["SOC Code"].apply(clean_soc)
    return df[["soc6", "Occupation Title", "AIOE"]].copy()


def load_work_context() -> pd.DataFrame:
    path = IDX_DIR / "Work Context.xlsx"
    df = pd.read_excel(path)
    df["soc6"] = df["O*NET-SOC Code"].apply(clean_soc)
    # filter scale and elements
    df = df[(df["Scale ID"] == "CX") & (df["Element Name"].isin(WC_ELEMENTS))]
    pivot = (
        df.pivot_table(
            index="soc6",
            columns="Element Name",
            values="Data Value",
            aggfunc="mean",
        )
        .reset_index()
    )
    pivot.columns.name = None
    return pivot


def load_job_zones() -> pd.DataFrame:
    path = IDX_DIR / "Job Zones.xlsx"
    df = pd.read_excel(path)
    df["soc6"] = df["O*NET-SOC Code"].apply(clean_soc)
    df = df[["soc6", "Job Zone"]].copy()
    df["job_zone_score"] = (df["Job Zone"] - 1) / 4 * 100
    return df[["soc6", "job_zone_score"]]


def build_components(wc: pd.DataFrame) -> pd.DataFrame:
    df = wc.rename(columns=WC_RENAME).copy()

    # Inversion for automation
    df["automation_inverted"] = 100 - df["degree_automation"]

    df["communication"] = df[["face_to_face", "public_speaking"]].mean(axis=1)
    df["responsibility"] = df[["impact_decisions", "health_safety"]].mean(axis=1)
    df["physical"] = df[["outdoors_weather", "physical_proximity"]].mean(axis=1)
    df["criticality"] = df[
        ["consequence_error", "freedom_decisions", "frequency_decisions"]
    ].mean(axis=1)
    if "structured_vs_unstructured" in df.columns:
        df["routine"] = df[["automation_inverted", "structured_vs_unstructured"]].mean(
            axis=1
        )
    else:
        df["routine"] = df["automation_inverted"]

    comps = df[
        [
            "soc6",
            "communication",
            "responsibility",
            "physical",
            "criticality",
            "routine",
        ]
    ].copy()
    return comps


def compute_theta(row) -> float:
    vals = [
        row["communication"],
        row["responsibility"],
        row["physical"],
        row["criticality"],
        row["routine"],
        row["job_zone_score"],
    ]
    if any(pd.isna(v) for v in vals):
        return np.nan
    return np.mean(vals) / 100.0


def main() -> None:
    aioe = load_aioe()
    wc_raw = load_work_context()
    comps = build_components(wc_raw)
    jobz = load_job_zones()

    # Merge onto AIOE universe
    df = aioe.merge(comps, on="soc6", how="left").merge(jobz, on="soc6", how="left")

    # theta
    df["theta"] = df.apply(compute_theta, axis=1)
    theta_min = df["theta"].min(skipna=True)
    df["theta_min"] = theta_min

    df["missing_context_or_zone"] = df[
        [
            "communication",
            "responsibility",
            "physical",
            "criticality",
            "routine",
            "job_zone_score",
        ]
    ].isna().any(axis=1)

    df["C_AIOE"] = np.where(
        df["missing_context_or_zone"],
        np.nan,
        df["AIOE"] * (1 - (df["theta"] - theta_min)),
    )

    # Validation prints
    total = len(df)
    valid_theta = df["theta"].notna().sum()
    missing = df["missing_context_or_zone"].sum()
    print(f"SOCs in AIOE: {total}")
    print(f"SOCs with valid theta: {valid_theta}")
    print(f"SOCs missing context/zone: {missing}")
    if valid_theta:
        print(f"theta min/max: {df['theta'].min():.4f} / {df['theta'].max():.4f}")
        print("\nTop 5 theta:")
        print(df[df["theta"].notna()].nlargest(5, "theta")[["soc6", "theta"]])
        print("\nBottom 5 theta:")
        print(df[df["theta"].notna()].nsmallest(5, "theta")[["soc6", "theta"]])
        print("\nTop 5 C_AIOE:")
        print(df[df["C_AIOE"].notna()].nlargest(5, "C_AIOE")[["soc6", "C_AIOE"]])

    # Save outputs
    df.to_excel(OUT_XLSX, index=False)
    df.to_csv(OUT_CSV, index=False)
    print(f"Wrote: {OUT_XLSX}")
    print(f"Wrote: {OUT_CSV}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
