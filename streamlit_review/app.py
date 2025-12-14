#!/usr/bin/env python3
"""
Streamlit app to annotate AI-requirement classifications.
Now builds the sample as the union of ads marked True/Maybe in v6, v7, or v7 rerun.
New sample/annotations files are generated; old ones (sample_old.json, annotations_old.json) are left untouched.
"""
from __future__ import annotations

import bz2
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "Results Datasets" / "ai_mentions" / "results" / "requirements"
RESULTS_V6 = RESULTS_DIR / "v6"
RESULTS_V7 = RESULTS_DIR / "v7"
RESULTS_V7_RERUN = RESULTS_DIR / "v7_rerun" / "ai_job_requirements_all_2010_2024_v7_rerun.json"
RESULTS_V7_RERUN2 = RESULTS_DIR / "v7_rerun2" / "ai_job_requirements_all_2010_2024_v7_rerun2.json"
TEXT_DIR = ROOT / "Base Dataset" / "Data" / "699_SJMM_Data_TextualData_v10.0" / "sjmm_suf_ad_texts"
DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLE_PATH = DATA_DIR / "sample.json"
ANNOTATIONS_PATH = DATA_DIR / "annotations.json"

BUCKETS: List[Tuple[str, int, int]] = [
    ("recent", 2020, 2024),
    ("mid", 2015, 2019),
    ("early", 2010, 2014),
]

def _current_index_state(n: int) -> int:
    if "idx" not in st.session_state:
        st.session_state.idx = 0
    st.session_state.idx = max(0, min(n - 1, st.session_state.idx))
    return st.session_state.idx


@st.cache_data(show_spinner=False)
def _load_results_all_v6() -> Dict[int, Dict[str, dict]]:
    res: Dict[int, Dict[str, dict]] = {}
    if not RESULTS_V6.exists():
        return res
    for path in sorted(RESULTS_V6.glob("ai_job_requirements_all_*_v6.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for ys, ads in data.items():
            try:
                yi = int(ys)
            except Exception:
                continue
            if isinstance(ads, dict):
                res.setdefault(yi, {}).update(ads)
    return res


@st.cache_data(show_spinner=False)
def _load_results_v7() -> Dict[int, Dict[str, dict]]:
    res: Dict[int, Dict[str, dict]] = {}
    if not RESULTS_V7.exists():
        return res
    for path in sorted(RESULTS_V7.glob("ai_job_requirements_all_*_v7.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for ys, ads in data.items():
            try:
                yi = int(ys)
            except Exception:
                continue
            if isinstance(ads, dict):
                res.setdefault(yi, {}).update(ads)
    return res


@st.cache_data(show_spinner=False)
def _load_results_v7_rerun() -> Dict[int, Dict[str, dict]]:
    rerun: Dict[int, Dict[str, dict]] = {}
    if not RESULTS_V7_RERUN.exists():
        return rerun
    try:
        data = json.loads(RESULTS_V7_RERUN.read_text(encoding="utf-8"))
    except Exception:
        return rerun
    for ys, ads in data.items():
        try:
            yi = int(ys)
        except Exception:
            continue
        if isinstance(ads, dict):
            rerun.setdefault(yi, {}).update(ads)
    return rerun


@st.cache_data(show_spinner=False)
def _load_results_v7_rerun2() -> Dict[int, Dict[str, dict]]:
    rerun: Dict[int, Dict[str, dict]] = {}
    if not RESULTS_V7_RERUN2.exists():
        return rerun
    try:
        data = json.loads(RESULTS_V7_RERUN2.read_text(encoding="utf-8"))
    except Exception:
        return rerun
    for ys, ads in data.items():
        try:
            yi = int(ys)
        except Exception:
            continue
        if isinstance(ads, dict):
            rerun.setdefault(yi, {}).update(ads)
    return rerun


@st.cache_data(show_spinner=False)
def _load_texts(years: List[int]) -> Dict[str, str]:
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


@st.cache_data(show_spinner=False)
def _load_sample(df: pd.DataFrame) -> List[dict]:
    def _valid(sample_obj: List[dict]) -> bool:
        if not isinstance(sample_obj, list) or not sample_obj:
            return False
        required = {"ad_id", "year", "text"}
        return required.issubset(set(sample_obj[0].keys()))

    if SAMPLE_PATH.exists():
        try:
            loaded = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
            if _valid(loaded):
                return loaded
        except Exception:
            pass

    sample = df.to_dict(orient="records")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_PATH.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    return sample


def _migrate_sample_fields(sample: List[dict], records_by_id: Dict[str, dict]) -> None:
    """
    Ensure new fields (e.g., v7_rerun2, true_votes_v7_runs) exist on rows loaded
    from an older sample.json. Does not change existing annotations.
    """
    for row in sample:
        src = records_by_id.get(row.get("ad_id"))
        if not src:
            continue
        # Populate missing label/reason/keywords for v7_rerun2
        if "label_v7_rerun2" not in row:
            row["label_v7_rerun2"] = src.get("label_v7_rerun2", "False")
        if "reason_v7_rerun2" not in row:
            row["reason_v7_rerun2"] = src.get("reason_v7_rerun2", "")
        if "keywords_v7_rerun2" not in row:
            row["keywords_v7_rerun2"] = src.get("keywords_v7_rerun2", [])
        # Recompute vote count if missing
        if "true_votes_v7_runs" not in row:
            row["true_votes_v7_runs"] = sum(
                int(lbl == "True")
                for lbl in (
                    row.get("label_v7"),
                    row.get("label_v7_rerun"),
                    row.get("label_v7_rerun2"),
                )
            )
        # Recompute agreement if missing
        if "agreement_v7_runs" not in row:
            l1 = row.get("label_v7")
            l2 = row.get("label_v7_rerun")
            l3 = row.get("label_v7_rerun2")
            if l1 == l2 == l3:
                row["agreement_v7_runs"] = 3
            elif l1 == l2 or l1 == l3 or l2 == l3:
                row["agreement_v7_runs"] = 2
            else:
                row["agreement_v7_runs"] = 0


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


def _refresh_flags(sample: List[dict]) -> None:
    """
    Recompute true/pos flags from labels so that Maybe counts as False for the
    tick columns. This keeps the table consistent even if an old sample.json
    had different flags.
    """
    for row in sample:
        lv6 = row.get("label_v6")
        lv7 = row.get("label_v7")
        lv7r = row.get("label_v7_rerun")
        lv7r2 = row.get("label_v7_rerun2")
        row["true_v6"] = lv6 == "True"
        row["true_v7"] = lv7 == "True"
        row["true_v7_rerun"] = lv7r == "True"
        row["true_v7_rerun2"] = lv7r2 == "True"
        row["pos_v6"] = row["true_v6"]
        row["pos_v7"] = row["true_v7"]
        row["pos_v7_rerun"] = row["true_v7_rerun"]
        row["pos_v7_rerun2"] = row["true_v7_rerun2"]


def _assign_bucket(year: int) -> str | None:
    for name, start, end in BUCKETS:
        if start <= year <= end:
            return name
    return None


def main() -> None:
    st.set_page_config(page_title="AI requirements annotation", layout="wide")
    st.title("AI requirements annotation (LLM outputs)")

    v6 = _load_results_all_v6()
    v7 = _load_results_v7()
    v7_rerun = _load_results_v7_rerun()
    v7_rerun2 = _load_results_v7_rerun2()
    if not v6 and not v7 and not v7_rerun and not v7_rerun2:
        st.error("No results found. Check v6/v7 and rerun files.")
        st.stop()

    years = sorted(set(v6.keys()) | set(v7.keys()) | set(v7_rerun.keys()) | set(v7_rerun2.keys()))
    texts = _load_texts(years)

    records = []
    for year in years:
        ad_ids = set()
        for src in (v6, v7, v7_rerun, v7_rerun2):
            if year in src:
                ad_ids.update(src[year].keys())
        for ad_id in ad_ids:
            txt = texts.get(ad_id)
            if not txt:
                continue
            row = {"ad_id": ad_id, "year": year, "text": txt}
            meta6 = (v6.get(year) or {}).get(ad_id, {})
            lab6 = str(meta6.get("ai_requirement") or "False").capitalize()
            row["label_v6"] = lab6 if lab6 in ("True", "Maybe") else "False"
            row["reason_v6"] = meta6.get("reason", "")
            row["keywords_v6"] = meta6.get("keywords", [])
            row["pos_v6"] = row["label_v6"] in ("True", "Maybe")
            row["true_v6"] = row["label_v6"] == "True"

            meta7 = (v7.get(year) or {}).get(ad_id, {})
            lab7 = str(meta7.get("ai_requirement") or "False").capitalize()
            row["label_v7"] = lab7 if lab7 in ("True", "Maybe") else "False"
            row["reason_v7"] = meta7.get("reason", "")
            row["keywords_v7"] = meta7.get("keywords", [])
            row["pos_v7"] = row["label_v7"] in ("True", "Maybe")
            row["true_v7"] = row["label_v7"] == "True"

            meta7r = (v7_rerun.get(year) or {}).get(ad_id, {})
            lab7r = str(meta7r.get("ai_requirement") or "False").capitalize()
            row["label_v7_rerun"] = lab7r if lab7r in ("True", "Maybe") else "False"
            row["reason_v7_rerun"] = meta7r.get("reason", "")
            row["keywords_v7_rerun"] = meta7r.get("keywords", [])
            row["pos_v7_rerun"] = row["label_v7_rerun"] in ("True", "Maybe")
            row["true_v7_rerun"] = row["label_v7_rerun"] == "True"

            meta7r2 = (v7_rerun2.get(year) or {}).get(ad_id, {})
            lab7r2 = str(meta7r2.get("ai_requirement") or "False").capitalize()
            row["label_v7_rerun2"] = lab7r2 if lab7r2 in ("True", "Maybe") else "False"
            row["reason_v7_rerun2"] = meta7r2.get("reason", "")
            row["keywords_v7_rerun2"] = meta7r2.get("keywords", [])
            row["pos_v7_rerun2"] = row["label_v7_rerun2"] in ("True", "Maybe")
            row["true_v7_rerun2"] = row["label_v7_rerun2"] == "True"

            row["changed_v7_vs_rerun"] = row["label_v7"] != row["label_v7_rerun"]
            row["changed_v6_vs_any"] = (row["label_v6"] != row["label_v7"]) or (row["label_v6"] != row["label_v7_rerun"])
            row["true_votes_v7_runs"] = sum(
                int(lbl == "True")
                for lbl in (row["label_v7"], row["label_v7_rerun"], row["label_v7_rerun2"])
            )
            row["agreement_v7_runs"] = 3 if (row["label_v7"] == row["label_v7_rerun"] == row["label_v7_rerun2"]) else (
                2 if (
                    row["label_v7"] == row["label_v7_rerun"] or
                    row["label_v7"] == row["label_v7_rerun2"] or
                    row["label_v7_rerun"] == row["label_v7_rerun2"]
                ) else 0
            )

            if row["pos_v6"] or row["pos_v7"] or row["pos_v7_rerun"]:
                records.append(row)

    df = pd.DataFrame(records)
    if df.empty:
        st.error("No data with text available after filtering True/Maybe across versions.")
        st.stop()

    records_by_id = {r["ad_id"]: r for r in records}
    sample = _load_sample(df)
    _migrate_sample_fields(sample, records_by_id)
    _refresh_flags(sample)
    annotations = _load_annotations()

    filled, filled_counts = _mark_progress(sample, annotations)
    total = len(sample)

    with st.sidebar:
        st.subheader("Progress")
        st.progress(filled / total if total else 0.0)
        st.write(f"Annotated: {filled}/{total}")
        st.write(f"True: {filled_counts['True']}, Maybe: {filled_counts['Maybe']}, False: {filled_counts['False']}")
        st.markdown("---")
        years_all = sorted({r["year"] for r in sample})
        year_sel = st.multiselect("Years", years_all, default=years_all)
        v6_filter = st.multiselect("v6 labels", ["True", "Maybe", "False"], default=["True", "Maybe", "False"])
        v7_filter = st.multiselect("v7 labels", ["True", "Maybe", "False"], default=["True", "Maybe", "False"])
        v7r_filter = st.multiselect("v7 rerun labels", ["True", "Maybe", "False"], default=["True", "Maybe", "False"])
        v7r2_filter = st.multiselect("v7 rerun2 labels", ["True", "Maybe", "False"], default=["True", "Maybe", "False"])
        pred_v7_filter = st.selectbox("Prediction (v7)", ["Any", "True", "Maybe", "False"], index=0)
        truth_filter = st.selectbox("Truth/annotation", ["Any", "True", "Maybe", "False", "Unannotated"], index=0)

        st.markdown("**Comparison filters**")
        mode = st.radio("Filter mode", ["None", "Preset", "Advanced"], index=1, horizontal=True)

        preset = None
        if mode == "Preset":
            preset = st.selectbox(
                "Preset comparison",
                [
                    "None",
                    "v7 == v7 rerun",
                    "v7 != v7 rerun",
                    "v7 = True AND v7 rerun = False",
                    "v7 = False AND v7 rerun = True",
                    "v7 = Maybe AND v7 rerun = True",
                    "v7 = True AND v7 rerun2 = False",
                    "v7 = False AND v7 rerun2 = True",
                ],
                index=0,
            )

        cond_a = cond_b = logic_op = None
        if mode == "Advanced":
            cols = st.columns(2)
            with cols[0]:
                ver_a = st.selectbox("Cond A version", ["v6", "v7", "v7_rerun"])
                op_a = st.selectbox("Cond A op", ["=", "!="], key="op_a")
                val_a = st.selectbox("Cond A value", ["True", "Maybe", "False"], key="val_a")
                cond_a = (ver_a, op_a, val_a)
            with cols[1]:
                ver_b = st.selectbox("Cond B version", ["v6", "v7", "v7_rerun"])
                op_b = st.selectbox("Cond B op", ["=", "!="], key="op_b")
                val_b = st.selectbox("Cond B value", ["True", "Maybe", "False"], key="val_b")
                cond_b = (ver_b, op_b, val_b)
            ver_c = st.selectbox("Cond C version", ["v6", "v7", "v7_rerun", "v7_rerun2"])
            op_c = st.selectbox("Cond C op", ["=", "!="], key="op_c")
            val_c = st.selectbox("Cond C value", ["True", "Maybe", "False"], key="val_c")
            cond_c = (ver_c, op_c, val_c)
            logic_op1 = st.radio("Combine A/B", ["AND", "OR"], horizontal=True)
            logic_op2 = st.radio("Combine with C", ["AND", "OR"], horizontal=True, key="logic2")

        filter_changed_v7_vs_rerun = st.checkbox("Filter: v7 differs from v7 rerun", value=False)
        filter_changed_any_v7_runs = st.checkbox("Filter: any difference among v7 runs", value=False, help="Keeps ads where v7, v7 rerun, and v7 rerun2 are not all the same.")
        filter_changed_v6_vs_any = st.checkbox("Filter: v6 differs from (v7 or v7 rerun)", value=False)
        filter_only_non_annotated = st.checkbox("Filter: only non-annotated postings", value=False)
        filter_none_true_v7_runs = st.checkbox("Filter: none of v7 runs is True", value=False)
        filter_at_least_two_true = st.checkbox("Filter: at least 2 of v7 runs are True", value=False)
        filter_exactly_one_true = st.checkbox("Filter: exactly 1 of v7 runs is True", value=False)
        filter_exactly_two_true = st.checkbox("Filter: exactly 2 of v7 runs are True", value=False)
        agreement_sel = st.selectbox("Filter by v7-run agreement level", ["Any", "3 (all same)", "2 (two match)", "0 (all different)"])
        jump_id = st.text_input("Jump to ad_id")
        if st.button("Jump") and jump_id:
            for i, row in enumerate(sample):
                if row["ad_id"] == jump_id:
                    st.session_state.idx = i
                    break

    if not sample:
        st.warning("Sample is empty. Check data availability.")
        st.stop()

    def cond_match(r, ver, op, val):
        label = r.get(f"label_{ver}")
        if op == "=":
            return label == val
        return label != val

    def apply_comparison(r):
        if mode == "None":
            return True
        if mode == "Preset":
            if preset == "None" or preset is None:
                return True
            if preset == "v7 == v7 rerun":
                return r["label_v7"] == r["label_v7_rerun"]
            if preset == "v7 != v7 rerun":
                return r["label_v7"] != r["label_v7_rerun"]
            if preset == "v7 = True AND v7 rerun = False":
                return r["label_v7"] == "True" and r["label_v7_rerun"] == "False"
            if preset == "v7 = False AND v7 rerun = True":
                return r["label_v7"] == "False" and r["label_v7_rerun"] == "True"
            if preset == "v7 = Maybe AND v7 rerun = True":
                return r["label_v7"] == "Maybe" and r["label_v7_rerun"] == "True"
            if preset == "v7 = True AND v7 rerun2 = False":
                return r["label_v7"] == "True" and r["label_v7_rerun2"] == "False"
            if preset == "v7 = False AND v7 rerun2 = True":
                return r["label_v7"] == "False" and r["label_v7_rerun2"] == "True"
            return True
        if mode == "Advanced" and cond_a and cond_b and cond_c and logic_op1 and logic_op2:
            a_ok = cond_match(r, *cond_a)
            b_ok = cond_match(r, *cond_b)
            c_ok = cond_match(r, *cond_c)
            first = (a_ok and b_ok) if logic_op1 == "AND" else (a_ok or b_ok)
            return (first and c_ok) if logic_op2 == "AND" else (first or c_ok)
        return True

    def matches_filters(r):
        if r["year"] not in year_sel:
            return False
        if r["label_v6"] not in v6_filter:
            return False
        if r["label_v7"] not in v7_filter:
            return False
        if r["label_v7_rerun"] not in v7r_filter:
            return False
        if r["label_v7_rerun2"] not in v7r2_filter:
            return False
        if pred_v7_filter != "Any" and r["label_v7"] != pred_v7_filter:
            return False
        # truth comes from annotations dict; if missing -> Unannotated
        truth_label = annotations.get(r["ad_id"], {}).get("label")
        if truth_filter != "Any":
            if truth_filter == "Unannotated" and truth_label is not None:
                return False
            if truth_filter != "Unannotated" and truth_label != truth_filter:
                return False
        if not apply_comparison(r):
            return False
        if filter_changed_v7_vs_rerun and not r.get("changed_v7_vs_rerun"):
            return False
        if filter_changed_any_v7_runs:
            if not (
                r.get("label_v7") == r.get("label_v7_rerun") == r.get("label_v7_rerun2")
            ):
                pass
            else:
                return False
        if filter_none_true_v7_runs and r.get("true_votes_v7_runs", 0) != 0:
            return False
        if filter_at_least_two_true and r.get("true_votes_v7_runs", 0) < 2:
            return False
        if filter_exactly_one_true and r.get("true_votes_v7_runs", 0) != 1:
            return False
        if filter_exactly_two_true and r.get("true_votes_v7_runs", 0) != 2:
            return False
        if agreement_sel != "Any":
            target = {"3 (all same)": 3, "2 (two match)": 2, "0 (all different)": 0}[agreement_sel]
            if r.get("agreement_v7_runs") != target:
                return False
        if filter_changed_v6_vs_any and not r.get("changed_v6_vs_any"):
            return False
        if filter_only_non_annotated and r["ad_id"] in annotations:
            return False
        return True

    filtered_indices = [i for i, r in enumerate(sample) if matches_filters(r)]
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

    def fmt_kw(kw_list):
        return " | ".join(kw_list) if kw_list else "—"

    st.markdown(
        f"**v6:** {row['label_v6']}  \n"
        f"• keywords: {fmt_kw(row.get('keywords_v6', []))}  \n"
        f"• reason: {row.get('reason_v6') or '—'}"
    )
    st.markdown(
        f"**v7:** {row['label_v7']}  \n"
        f"• keywords: {fmt_kw(row.get('keywords_v7', []))}  \n"
        f"• reason: {row.get('reason_v7') or '—'}"
    )
    st.markdown(
        f"**v7 rerun:** {row['label_v7_rerun']}  \n"
        f"• keywords: {fmt_kw(row.get('keywords_v7_rerun', []))}  \n"
        f"• reason: {row.get('reason_v7_rerun') or '—'}"
    )
    st.markdown(
        f"**v7 rerun2:** {row['label_v7_rerun2']}  \n"
        f"• keywords: {fmt_kw(row.get('keywords_v7_rerun2', []))}  \n"
        f"• reason: {row.get('reason_v7_rerun2') or '—'}"
    )
    st.markdown(f"**True votes (v7 runs):** {row.get('true_votes_v7_runs',0)}/3")
    st.text_area("Ad text", value=row.get("text", ""), height=320)

    current_ann = annotations.get(row["ad_id"], {})
    col1, col2, col3 = st.columns([1, 1, 2])
    label_options = ["—", "True", "Maybe", "False"]
    default_label = current_ann.get("label")
    if default_label not in label_options:
        default_label = "—"
    with col1:
        label = st.radio(
            "Your label",
            options=label_options,
            index=label_options.index(default_label),
            key=f"label_{row['ad_id']}",
            help="Leave unset to avoid saving while navigating.",
        )
    with col2:
        flag = st.checkbox("Flag", value=bool(current_ann.get("flag")), key=f"flag_{row['ad_id']}")
    with col3:
        note = st.text_input(
            "Reason (optional)",
            value=current_ann.get("reason_note", ""),
            key=f"note_{row['ad_id']}",
        )

    if label != "—":
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
                "label_v6": r["label_v6"],
                "label_v7": r["label_v7"],
                "label_v7_rerun": r["label_v7_rerun"],
                "label_v7_rerun2": r["label_v7_rerun2"],
                "pos_v6": r["pos_v6"],
                "pos_v7": r["pos_v7"],
                "pos_v7_rerun": r["pos_v7_rerun"],
                "pos_v7_rerun2": r["pos_v7_rerun2"],
                "user_label": ann_labels.get(r["ad_id"], ""),
                "flag": bool(annotations.get(r["ad_id"], {}).get("flag")),
                "true_votes_v7_runs": r.get("true_votes_v7_runs", 0),
            }
        )
    st.dataframe(pd.DataFrame(sample_view))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Error: {e}")
