#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


HERE = Path(__file__).resolve()
AI_DIR = HERE.parents[1]
ROOT = HERE.parents[2]

# Ensure we import the project-local detector (use the fulltext module where helpers live)
sys.path.insert(0, str(AI_DIR))
import importlib, importlib.machinery
try:
    detector = importlib.import_module('detect_ai_mentions_fulltext')
except ModuleNotFoundError:
    # Fallback: load directly from file
    loader = importlib.machinery.SourceFileLoader('detect_ai_mentions_fulltext', str(AI_DIR / 'detect_ai_mentions_fulltext.py'))
    detector = loader.load_module()
compile_patterns = detector.compile_patterns
load_keywords = detector.load_keywords
KEYWORDS_PATH = detector.KEYWORDS_PATH


CASE_PATH = HERE.parent / "cases.json"


def normalize_text(s: str) -> str:
    # Normalize Unicode hyphens/dashes to ASCII hyphen
    return (
        s.replace("\u2010", "-")  # hyphen
        .replace("\u2011", "-")    # non-breaking hyphen
        .replace("\u2012", "-")    # figure dash
        .replace("\u2013", "-")    # en dash
        .replace("\u2014", "-")    # em dash
        .replace("\u2212", "-")    # minus sign
    )


@dataclass
class CaseResult:
    text: str
    expected: List[str]
    found: List[str]
    missing_keywords: List[str]
    false_positives: List[str]


def run_cases(cases: Dict[str, List[dict]]) -> Tuple[List[CaseResult], List[CaseResult]]:
    keywords = load_keywords(KEYWORDS_PATH)
    patterns = compile_patterns(keywords)
    keyword_set = {k.lower() for k in keywords}

    positives_out: List[CaseResult] = []
    negatives_out: List[CaseResult] = []

    # Positive cases
    for c in cases.get("positives", []):
        text = normalize_text(c["text"])
        expect = [e.lower() for e in c.get("expect", [])]
        found: List[str] = []
        for kw, pats in patterns.items():
            if any(p.search(text) for p in pats):
                found.append(kw.lower())
        missing = [e for e in expect if e not in found]
        # allowed extra matches are not necessarily false positives in positive cases,
        # but we can still surface unexpected ones for review
        extras = [k for k in found if k not in expect]
        # Highlight expected keywords not present in the lexicon
        absent = [e for e in expect if e not in keyword_set]
        positives_out.append(CaseResult(text, expect, sorted(set(found)), absent, sorted(set(extras))))

    # Negative cases
    for c in cases.get("negatives", []):
        text = normalize_text(c["text"])
        found: List[str] = []
        for kw, pats in patterns.items():
            if any(p.search(text) for p in pats):
                found.append(kw.lower())
        negatives_out.append(CaseResult(text, [], sorted(set(found)), [], sorted(set(found))))

    return positives_out, negatives_out


def main() -> int:
    cases = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    pos, neg = run_cases(cases)

    # Summaries
    pos_total = len(pos)
    pos_ok = sum(1 for r in pos if not r.missing_keywords and not r.missing_keywords)
    neg_total = len(neg)
    neg_ok = sum(1 for r in neg if not r.false_positives)

    print(f"Positive cases: {pos_ok}/{pos_total} met expected keywords (see details below)")
    print(f"Negative cases: {neg_ok}/{neg_total} with zero matches")

    # Report positives with issues
    for r in pos:
        if r.missing_keywords or r.missing_keywords or r.false_positives or r.missing_keywords:
            print("\n[POS]", r.text)
            if r.expected:
                print("  expect:", r.expected)
            print("  found:", r.found)
            if r.missing_keywords:
                print("  missing expected:", r.missing_keywords)
            if r.false_positives:
                print("  extra matches:", r.false_positives)
            # Lexicon gaps
            missing_in_lex = [e for e in r.expected if e not in {k.lower() for k in load_keywords(KEYWORDS_PATH)}]
            if missing_in_lex:
                print("  absent in ai_keywords.json:", missing_in_lex)

    # Report negatives with any matches
    for r in neg:
        if r.false_positives:
            print("\n[NEG]", r.text)
            print("  unexpected matches:", r.false_positives)

    # Simple exit code heuristic: fail if any negative had a match or if any positive missed an expected keyword
    any_neg_fail = any(r.false_positives for r in neg)
    any_pos_missing = any(r.missing_keywords for r in pos)
    if any_neg_fail or any_pos_missing:
        print("\nResult: FAIL (see issues above)")
        return 1
    print("\nResult: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
