#!/usr/bin/env python3
"""
Streamlit app to annotate AI-requirement classifications.
Creates a fixed stratified sample (200 ads: 100 False, 50 Maybe, 50 True)
drawn by year buckets: 50% from 2020–2024, 30% from 2015–2019, 20% from 2010–2014.
Annotations (label, optional note, optional flag) are saved on every change.
"""
from __future__ import annotations

import bz2
import json
import os
import random
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "Results Datasets" / "ai_mentions" / "results" / "requirements"
TEXT_DIR = ROOT / "Base Dataset" / "Data" / "699_SJMM_Data_TextualData_v10.0" / "sjmm_suf_ad_texts"
DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLE_PATH = DATA_DIR / "sample.json"
ANNOTATIONS_PATH = DATA_DIR / "annotations.json"
BATCH_RERUN_FILE = RESULTS_DIR / "ai_job_requirements_all_2010_2024_v6_rerun_tm_all.json"

BUCKETS: List[Tuple[str, int, int]] = [
    ("recent", 2020, 2024),
    ("mid", 2015, 2019),
    ("early", 2010, 2014),
]


@st.cache_data(show_spinner=False)
def _load_results_all() -> Dict[int, Dict[str, dict]]:
    """Load all original v6 results (per-year files)."""
    all_results: Dict[int, Dict[str, dict]] = {}
    if not RESULTS_DIR.exists():
        return all_results
    for path in sorted(RESULTS_DIR.glob("ai_job_requirements_all_*_v6.json")):
        # skip the rerun combined file
        if "2010_2024_v6_rerun_tm_all" in path.name:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for ys, ads in data.items():
            try:
                yi = int(ys)
            except Exception:
                continue
            if not isinstance(ads, dict):
                continue
            all_results.setdefault(yi, {}).update(ads)
    return all_results


@st.cache_data(show_spinner=False)
def _load_results_rerun() -> Dict[int, Dict[str, dict]]:
    """Load rerun combined file (True/Maybe) 2010-2024."""
    rerun: Dict[int, Dict[str, dict]] = {}
    if not BATCH_RERUN_FILE.exists():
        return rerun
    try:
        data = json.loads(BATCH_RERUN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return rerun
    for ys, ads in data.items():
        try:
            yi = int(ys)
        except Exception:
            continue
        if not isinstance(ads, dict):
            continue
        rerun.setdefault(yi, {}).update(ads)
    return rerun


@st.cache_data(show_spinner=False)
def _load_texts(years: List[int]) -> Dict[str, str]:
    """Load ad texts for the specified years from compressed JSONL files."""
    texts: Dict[str, str] = {}
    for year in sorted(set(years)):
        p = TEXT_DIR / f"ads_sjmm_{year}.jsonl.bz2"
        if not p.exists():
            continue
        try:
            with bz2.open(p, "rt", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    ad_id = obj.get("adve_iden_adve")
                    txt = obj.get("adve_text_adve") or ""
                    if isinstance(ad_id, str) and isinstance(txt, str) and txt.strip():
                        texts[ad_id] = txt
        except Exception:
            continue
    return texts


def _build_df(rerun: Dict[int, Dict[str, dict]], original: Dict[int, Dict[str, dict]], texts: Dict[str, str]) -> pd.DataFrame:
    rows = []
    for year, ads in rerun.items():
        for ad_id, meta in ads.items():
            txt = texts.get(ad_id)
            if not txt:
                continue
            rr = str(meta.get("ai_requirement") or "False")
            if rr.lower() in ("true", "t", "yes"):
                rr = "True"
            elif rr.lower() == "maybe":
                rr = "Maybe"
            else:
                rr = "False"
            orig_meta = (original.get(year) or {}).get(ad_id, {})
            orr = str(orig_meta.get("ai_requirement") or "False")
            if orr.lower() in ("true", "t", "yes"):
                orr = "True"
            elif orr.lower() == "maybe":
                orr = "Maybe"
            else:
                orr = "False"
            rows.append(
                {
                    "ad_id": ad_id,
                    "year": year,
                    "rerun_label": rr,
                    "rerun_keywords": meta.get("keywords", []),
                    "rerun_reason": meta.get("reason", ""),
                    "orig_label": orr,
                    "orig_keywords": orig_meta.get("keywords", []),
                    "orig_reason": orig_meta.get("reason", ""),
                    "changed": orr != rr,
                    "text": txt,
                }
            )
    return pd.DataFrame(rows)


def _assign_bucket(year: int) -> str | None:
    for name, start, end in BUCKETS:
        if start <= year <= end:
            return name
    return None


@st.cache_data(show_spinner=False)
def _load_sample(df: pd.DataFrame) -> List[dict]:
    def _valid(sample_obj: List[dict]) -> bool:
        if not isinstance(sample_obj, list) or not sample_obj:
            return False
        # ensure required rerun fields exist to avoid KeyError
        required = {"ad_id", "year", "rerun_label", "orig_label", "text"}
        return required.issubset(set(sample_obj[0].keys()))

    if SAMPLE_PATH.exists():
        try:
            loaded = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
            if _valid(loaded):
                return loaded
        except Exception:
            pass

    sample = df.to_dict(orient="records")  # use full rerun set
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_PATH.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    return sample


def _load_annotations() -> Dict[str, dict]:
    if ANNOTATIONS_PATH.exists():
        try:
            return json.loads(ANNOTATIONS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_annotations(ann: Dict[str, dict]) -> None:
    ANNOTATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=ANNOTATIONS_PATH.parent, encoding="utf-8")
    json.dump(ann, tmp, ensure_ascii=False, indent=2)
    tmp.flush()
    os.fsync(tmp.fileno())
    tmp.close()
    Path(tmp.name).replace(ANNOTATIONS_PATH)


def _mark_progress(sample: List[dict], ann: Dict[str, dict]) -> Tuple[int, Dict[str, int]]:
    counts = {"True": 0, "Maybe": 0, "False": 0}
    filled = 0
    for row in sample:
        a = ann.get(row["ad_id"])
        if a and a.get("label") in counts:
            counts[a["label"]] += 1
            filled += 1
    return filled, counts


def _current_index_state(n: int) -> int:
    if "idx" not in st.session_state:
        st.session_state.idx = 0
    st.session_state.idx = max(0, min(n - 1, st.session_state.idx))
    return st.session_state.idx


def main() -> None:
    st.set_page_config(page_title="AI requirements annotation", layout="wide")
    st.title("AI requirements annotation (LLM outputs)")

    original = _load_results_all()
    rerun = _load_results_rerun()
    if not rerun:
        st.error("No rerun results found at ai_job_requirements_all_2010_2024_v6_rerun_tm_all.json")
        st.stop()

    years = sorted(rerun.keys())
    texts = _load_texts(years)
    df = _build_df(rerun, original, texts)
    if df.empty:
        st.error("No data with text available. Ensure ad text files are present.")
        st.stop()

    sample = _load_sample(df)
    annotations = _load_annotations()

    filled, filled_counts = _mark_progress(sample, annotations)
    total = len(sample)

    # Sidebar: progress and filters
    with st.sidebar:
        st.subheader("Progress")
        st.progress(filled / total if total else 0.0)
        st.write(f"Annotated: {filled}/{total}")
        st.write(f"True: {filled_counts['True']}, Maybe: {filled_counts['Maybe']}, False: {filled_counts['False']}")
        st.markdown("---")
        years_all = sorted({r["year"] for r in sample})
        year_sel = st.multiselect("Years", years_all, default=years_all)
        label_sel = st.multiselect("Rerun labels", ["True", "Maybe", "False"], default=["True", "Maybe", "False"])
        orig_label_sel = st.multiselect("Original labels", ["True", "Maybe", "False"], default=["True", "Maybe", "False"])
        changed_only = st.checkbox("Only changed vs original", value=False)
        jump_id = st.text_input("Jump to ad_id")
        if st.button("Jump") and jump_id:
            for i, row in enumerate(sample):
                if row["ad_id"] == jump_id:
                    st.session_state.idx = i
                    break

    if not sample:
        st.warning("Sample is empty. Check data availability.")
        st.stop()

    # Apply filters
    filtered_indices = [
        i for i, r in enumerate(sample)
        if r["year"] in year_sel
        and r["rerun_label"] in label_sel
        and r["orig_label"] in orig_label_sel
        and (not changed_only or r.get("changed"))
    ]
    if not filtered_indices:
        st.warning("No records match current filters.")
        st.stop()

    if "idx" not in st.session_state or st.session_state.idx not in filtered_indices:
        st.session_state.idx = filtered_indices[0]

    idx = _current_index_state(len(sample))
    if idx not in filtered_indices:
        diffs = [(abs(i - idx), i) for i in filtered_indices]
        st.session_state.idx = sorted(diffs)[0][1]
        idx = st.session_state.idx

    row = sample[idx]
    st.subheader(f"Ad {idx + 1}/{len(sample)} (filtered {len(filtered_indices)}) | Year {row['year']} | ad_id {row['ad_id']}")
    st.markdown(f"**Rerun label:** {row['rerun_label']} | **Orig label:** {row['orig_label']} | **Changed:** {row['changed']}")
    st.markdown(f"**Rerun keywords:** {', '.join(row.get('rerun_keywords', [])) or '—'}")
    st.markdown(f"**Rerun reason:** {row.get('rerun_reason') or '—'}")
    st.markdown(f"**Orig keywords:** {', '.join(row.get('orig_keywords', [])) or '—'}")
    st.markdown(f"**Orig reason:** {row.get('orig_reason') or '—'}")
    st.text_area("Ad text", value=row.get("text", ""), height=320)

    current_ann = annotations.get(row["ad_id"], {})
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        label = st.radio(
            "Your label",
            options=["True", "Maybe", "False"],
            index=["True", "Maybe", "False"].index(current_ann.get("label", row.get("rerun_label", "True"))),
            key=f"label_{row['ad_id']}",
        )
    with col2:
        flag = st.checkbox("Flag", value=bool(current_ann.get("flag")), key=f"flag_{row['ad_id']}")
    with col3:
        note = st.text_input(
            "Reason (optional)",
            value=current_ann.get("reason_note", ""),
            key=f"note_{row['ad_id']}",
        )

    # Auto-save on change
    new_ann = {
        "label": label,
        "reason_note": note,
        "flag": flag,
    }
    if new_ann != current_ann:
        annotations[row["ad_id"]] = new_ann
        _save_annotations(annotations)
        st.toast("Saved", icon="💾")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Prev"):
            try:
                pos = filtered_indices.index(idx)
                if pos > 0:
                    st.session_state.idx = filtered_indices[pos - 1]
                    st.rerun()
            except ValueError:
                pass
    with c2:
        if st.button("Next"):
            try:
                pos = filtered_indices.index(idx)
                if pos < len(filtered_indices) - 1:
                    st.session_state.idx = filtered_indices[pos + 1]
                    st.rerun()
            except ValueError:
                pass

    st.markdown("---")
    st.subheader("Sample overview (filtered)")
    ann_labels = {k: v.get("label") for k, v in annotations.items()}
    sample_view = []
    for i in filtered_indices:
        r = sample[i]
        sample_view.append(
            {
                "ad_id": r["ad_id"],
                "year": r["year"],
                "bucket": _assign_bucket(r["year"]),
                "orig_label": r["orig_label"],
                "rerun_label": r["rerun_label"],
                "changed": r.get("changed"),
                "user_label": ann_labels.get(r["ad_id"], ""),
                "flag": bool(annotations.get(r["ad_id"], {}).get("flag")),
            }
        )
    st.dataframe(pd.DataFrame(sample_view))


if __name__ == "__main__":
    main()
