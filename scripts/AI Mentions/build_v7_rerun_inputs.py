#!/usr/bin/env python3
"""
Build a v7 rerun batch input containing exactly the ads that were True/Maybe
in the original v7 results (2010–2024). This script does NOT modify the
existing batch script and uses the v7 prompt from prompts/v7.txt.
"""
from __future__ import annotations

import argparse
import bz2
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple


ROOT = Path(__file__).resolve().parents[2]
RES_DIR = ROOT / "Results Datasets" / "ai_mentions"
V7_RESULTS_DIR = RES_DIR / "results" / "requirements" / "v7"
PROMPT_PATH = RES_DIR / "prompts" / "v7.txt"
BATCH_DIR = RES_DIR / "batches" / "requirements" / "2010_2024" / "v7_rerun"
BATCH_JSONL = BATCH_DIR / "ai_requirements_batch_all_2010_2024_v7_rerun_input.jsonl"
SUMMARY_PATH = BATCH_DIR / "ai_requirements_batch_all_2010_2024_v7_rerun_summary.json"
TEXT_DIR = ROOT / "Base Dataset" / "Data" / "699_SJMM_Data_TextualData_v10.0" / "sjmm_suf_ad_texts"

MODEL = "gpt-5-mini"


def load_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise SystemExit(f"Prompt file not found: {PROMPT_PATH}")
    txt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not txt:
        raise SystemExit(f"Prompt file is empty: {PROMPT_PATH}")
    return txt


def load_v7_true_maybe() -> Dict[int, Set[str]]:
    """
    Return {year: {ad_id}} for ads labeled True/Maybe in v7 results.
    """
    targets: Dict[int, Set[str]] = {}
    for path in sorted(V7_RESULTS_DIR.glob("ai_job_requirements_all_*_v7.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for y_str, ads in data.items():
            try:
                year = int(y_str)
            except Exception:
                continue
            for ad_id, payload in (ads or {}).items():
                lab = str(payload.get("ai_requirement", "False")).capitalize()
                if lab in {"True", "Maybe"}:
                    targets.setdefault(year, set()).add(ad_id)
    return targets


def load_texts_for_year(year: int, ids: Set[str]) -> Dict[str, str]:
    """
    Load full text for the given ad_ids in a specific year.
    """
    idx: Dict[str, str] = {}
    p = TEXT_DIR / f"ads_sjmm_{year}.jsonl.bz2"
    if not p.exists():
        return idx
    with bz2.open(p, "rt", encoding="utf-8") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            ad = obj.get("adve_iden_adve")
            if ad not in ids:
                continue
            txt = obj.get("adve_text_adve") or ""
            if isinstance(txt, str) and txt.strip():
                idx[ad] = txt
    return idx


def build_jsonl(prompt: str, targets: Dict[int, Set[str]]) -> Tuple[int, List[str]]:
    """
    Write the batch JSONL and return (count, missing list).
    """
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    schema = {
        "name": "ai_requirement_simple",
        "schema": {
            "type": "object",
            "properties": {
                "ai_requirement": {"type": "string", "enum": ["True", "Maybe", "False"]},
                "reason": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["ai_requirement", "reason", "keywords"],
            "additionalProperties": False,
        },
        "strict": True,
    }

    written = 0
    missing: List[str] = []
    with open(BATCH_JSONL, "w", encoding="utf-8") as out:
        for year in sorted(targets):
            idx = load_texts_for_year(year, targets[year])
            for ad_id in sorted(targets[year]):
                txt = idx.get(ad_id)
                if not txt:
                    missing.append(f"{year}|{ad_id}")
                    continue
                body = {
                    "model": MODEL,
                    "response_format": {"type": "json_schema", "json_schema": schema},
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": json.dumps({"ad_id": ad_id, "text": txt}, ensure_ascii=False)},
                    ],
                }
                rec = {
                    "custom_id": f"{year}|{ad_id}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": body,
                }
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1
    return written, missing


def summarize(written: int, missing: List[str]) -> None:
    summary = {
        "written": written,
        "missing_texts": missing,
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Written: {written}")
    if missing:
        print(f"Missing texts for {len(missing)} ads (see summary file).")
    print(f"JSONL: {BATCH_JSONL}")
    print(f"Summary: {SUMMARY_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build v7 rerun batch input (True/Maybe only).")
    parser.add_argument("--start-year", type=int, default=2010, help="Start year inclusive (default 2010).")
    parser.add_argument("--end-year", type=int, default=2024, help="End year inclusive (default 2024).")
    args = parser.parse_args()

    prompt = load_prompt()
    targets_all = load_v7_true_maybe()
    targets = {y: ids for y, ids in targets_all.items() if args.start_year <= y <= args.end_year}

    if not targets:
        raise SystemExit("No targets found for the specified year span.")

    written, missing = build_jsonl(prompt, targets)
    summarize(written, missing)


if __name__ == "__main__":
    main()
