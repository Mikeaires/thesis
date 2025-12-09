#!/usr/bin/env python3
from __future__ import annotations

import bz2
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
import argparse


ROOT = Path(__file__).resolve().parents[2]
TEXT_BASE = ROOT / "Base Dataset" / "Data" / "699_SJMM_Data_TextualData_v10.0" / "sjmm_suf_ad_texts"
OUTPUT_PATH = ROOT / "Results Datasets" / "ai_mentions" / "ai_keyword_matches_fulltext.json"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
KEYWORDS_PATH = ROOT / "External datasets" / "ai_keywords.json"

# Word-boundary and hyphen handling
WORD_CLASS = r"\w"
HYPHENS = "-\u2010\u2011\u2012\u2013\u2014\u2212"


def load_keywords(path: Path) -> List[str]:
    """Load keywords from a list or {category: [list]} JSON file."""
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"AI keywords file is missing or empty: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items: List[str] = []
        for v in data.values():
            if isinstance(v, list):
                items.extend([str(x) for x in v])
        data_list = items
    elif isinstance(data, list):
        data_list = [str(x) for x in data]
    else:
        raise ValueError("ai_keywords.json must be a list or a {category: [list]} dictionary")
    return sorted({k.strip() for k in data_list if k and k.strip()})


def compile_patterns(keywords: List[str]) -> Dict[str, List[re.Pattern]]:
    """Compile robust regex patterns per keyword (AI/KI/LLM safe handling)."""
    patterns: Dict[str, List[re.Pattern]] = {}
    letters_lower = r"a-zäöüß"
    for kw in keywords:
        escaped = re.escape(kw)
        pats: List[re.Pattern] = []
        kw_upper = kw.upper()
        if kw_upper in {"AI", "KI", "LLM"}:
            # Case-sensitive standalone
            pats.append(re.compile(rf"(?<!{WORD_CLASS}){kw_upper}(?!{WORD_CLASS})"))
            # Allow hyphen/dash/slash compounds (AI-..., AI/...)
            pats.append(re.compile(rf"(?<!{WORD_CLASS}){kw_upper}(?=[{HYPHENS}/])"))
            # Allow lowercase continuation (AIenabled, KIgestützt, LLMs)
            pats.append(re.compile(rf"(?<!{WORD_CLASS}){kw_upper}(?=[{letters_lower}])"))
            # LLM plural/apostrophe
            if kw_upper == "LLM":
                pats.append(re.compile(rf"(?<!{WORD_CLASS}){kw_upper}(?:s\b|['’]s\b)"))
        else:
            # German 'künstliche Intelligenz' (incl. adjectival endings and 'kuenstliche')
            if kw.lower() in ("künstliche intelligenz", "kuenstliche intelligenz"):
                pats.append(re.compile(r"(?i)k[üu]nstlich(?:e|er|en|em|es)?\s+intelligenz"))
                patterns[kw] = pats
                continue
            # Default: case-insensitive word-ish boundaries
            pats.append(re.compile(rf"(?i)(?<!{WORD_CLASS}){escaped}(?!{WORD_CLASS})"))
        patterns[kw] = pats
    return patterns


def iter_year_files(base: Path, start_year: int = 2005, end_year: int | None = None) -> Iterable[Tuple[int, Path]]:
    year_re = re.compile(r"(\d{4})")
    for p in sorted(base.glob("ads_sjmm_*.jsonl.bz2")):
        m = year_re.search(p.name)
        if not m:
            continue
        year = int(m.group(1))
        if year >= start_year and (end_year is None or year <= end_year):
            yield year, p


def find_matches_with_context(text: str, patterns: Dict[str, List[re.Pattern]], ctx: int = 30) -> List[Dict[str, str]]:
    # Normalize hyphens/dashes for matching while preserving original text for snippets
    norm = (
        text.replace("\u2010", "-")
            .replace("\u2011", "-")
            .replace("\u2012", "-")
            .replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace("\u2212", "-")
    )
    results: List[Dict[str, str]] = []
    for kw, pats in patterns.items():
        seen: set[Tuple[int, int]] = set()  # avoid double counting same span for multiple variants
        for pat in pats:
            for m in pat.finditer(norm):
                a, b = m.start(), m.end()
                if (a, b) in seen:
                    continue
                seen.add((a, b))
                before = text[max(0, a - ctx):a]
                after = text[b:b + ctx]
                snippet = f"{before}«{text[a:b]}»{after}"
                results.append({
                    "keyword": kw,
                    "folder": "fulltext",
                    "text": snippet,
                })
    return results


def scan_fulltext(start_year: int = 2005, end_year: int | None = None) -> None:
    keywords = load_keywords(KEYWORDS_PATH)
    patterns = compile_patterns(keywords)

    results: Dict[str, Dict[str, List[Dict[str, str]]]] = {}

    for year, path in iter_year_files(TEXT_BASE, start_year=start_year, end_year=end_year):
        opener = bz2.open if path.suffix == ".bz2" else open
        with opener(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ad_id = obj.get("adve_iden_adve")
                text = obj.get("adve_text_adve") or ""
                if not ad_id or not isinstance(text, str) or not text:
                    continue

                # Use a wider context window (60 chars on each side)
                matches = find_matches_with_context(text, patterns, ctx=60)
                if matches:
                    bucket = results.setdefault(str(year), {})
                    bucket[ad_id] = matches

    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote fulltext matches to {OUTPUT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect AI keyword mentions in full ad text.")
    parser.add_argument("--start-year", type=int, default=2005, help="First year to include (default: 2005)")
    parser.add_argument("--end-year", type=int, default=None, help="Last year to include (inclusive). If omitted, scans to the latest available year.")
    args = parser.parse_args()
    scan_fulltext(start_year=args.start_year, end_year=args.end_year)
