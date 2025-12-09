#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[2]
MATCH_PATH = ROOT / "Results Datasets" / "ai_mentions" / "ai_keyword_matches_fulltext.json"
OUT_PATH = ROOT / "Results Datasets" / "ai_mentions" / "ai_keyword_matches_validated.json"
CACHE_PATH = ROOT / "Results Datasets" / "ai_mentions" / ".validation_cache.json"


def load_env() -> None:
    # Try python-dotenv if available
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(ROOT / ".env")
    except Exception:
        # Minimal fallback: read .env lines into the env
        env_path = ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip()
                if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                    v = v[1:-1]
                os.environ.setdefault(k.strip(), v)


def get_openai_client():
    """Return a callable that takes messages and returns JSON text."""
    load_env()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Put it in .env or your environment.")

    # Prefer new SDK
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI()

        def _call(model: str, messages: List[dict], json_mode: bool = True) -> str:
            kwargs = {}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                **kwargs,
            )
            return resp.choices[0].message.content or "{}"

        return _call
    except Exception:
        pass

    # Fallback to legacy SDK
    try:
        import openai  # type: ignore

        openai.api_key = api_key

        def _call(model: str, messages: List[dict], json_mode: bool = True) -> str:
            kwargs = {}
            if json_mode:
                # legacy JSON mode via system instruction
                messages = [{"role": "system", "content": "Return pure JSON only."}] + messages
            resp = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=0,
            )
            return resp["choices"][0]["message"]["content"]

        return _call
    except Exception as e:
        raise RuntimeError("Failed to initialize OpenAI client. Install `openai` package.") from e


def digest(item: dict) -> str:
    h = hashlib.sha256()
    h.update((item.get("keyword", "") + "\n" + item.get("text", "")).encode("utf-8"))
    return h.hexdigest()


def iter_tasks(matches: dict, start_year: int | None, end_year: int | None) -> Iterable[Tuple[str, str, dict]]:
    years = sorted(matches.keys())
    for y in years:
        yi = int(y)
        if start_year is not None and yi < start_year:
            continue
        if end_year is not None and yi > end_year:
            continue
        for ad_id, mlist in matches[y].items():
            for m in mlist:
                keyword = (m.get("keyword") or "").strip()
                text = (m.get("text") or "").strip()
                if not keyword or not text:
                    continue
                yield y, ad_id, {"keyword": keyword, "text": text}


SYSTEM_PROMPT = (
    "You are an expert annotator. For each input snippet and keyword, decide if the keyword "+
    "refers to an Artificial Intelligence topic in context, or is a non-AI usage. Return strict JSON."
)


def build_messages(batch: List[dict]) -> List[dict]:
    # Clear task: for each (keyword, snippet), decide if the keyword refers to an AI topic in this context.
    # No predefined categories; the model can optionally propose a short free-text topic.
    instructions = {
        "task": "ai_context_classification",
        "schema": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "idx": {"type": "integer"},
                            "keyword": {"type": "string"},
                            "ai_context": {"type": "boolean"},
                            "topic": {"type": "string"},
                            "reason": {"type": "string"}
                        },
                        "required": ["idx", "keyword", "ai_context"]
                    }
                }
            },
            "required": ["results"]
        },
        "guidelines": [
            "Consider only the provided snippet; do not infer beyond it.",
            "Mark ai_context=true when the usage clearly refers to Artificial Intelligence (methods, models, tools, roles, or companies like ChatGPT/OpenAI in an AI sense).",
            "Mark ai_context=false when the letters match but the meaning is non‑AI (e.g., KI as part of 'Kinder' or 'KIA', AIM/AIMS, generic abbreviations).",
            "Hyphenated forms and compounds (e.g., KI‑gestützt, AI‑enabled) count as AI if used in an AI/tech context.",
            "If context is ambiguous or insufficient, prefer ai_context=false and explain briefly in reason.",
            "Optionally include a short free‑text topic (e.g., 'NLP', 'LLM', 'computer vision', 'robotics'), otherwise leave it empty."
        ]
    }
    items = []
    for i, it in enumerate(batch):
        items.append({"idx": i, "keyword": it["keyword"], "snippet": it["text"]})

    content = json.dumps({"instructions": instructions, "items": items}, ensure_ascii=False)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def parse_json(s: str) -> dict:
    s = s.strip()
    # strip code fences if present
    if s.startswith("```") and s.endswith("```"):
        s = s.strip("`")
    # find first { ... } block
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1:
        s = s[start : end + 1]
    try:
        return json.loads(s)
    except Exception:
        return {"results": []}


def main():
    ap = argparse.ArgumentParser(description="Validate AI keyword matches using GPT (4o-mini)")
    ap.add_argument("--model", default="gpt-4o-mini", help="OpenAI model (default: gpt-4o-mini)")
    ap.add_argument("--start-year", type=int, default=None)
    ap.add_argument("--end-year", type=int, default=None)
    ap.add_argument("--batch-size", type=int, default=20)
    ap.add_argument("--limit", type=int, default=None, help="Limit number of match items to process")
    args = ap.parse_args()

    if not MATCH_PATH.exists():
        raise SystemExit(f"Matches file not found: {MATCH_PATH}")

    matches = json.loads(MATCH_PATH.read_text(encoding="utf-8"))

    # Load cache
    cache: Dict[str, dict] = {}
    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    # Prepare task list (with dedup/caching)
    tasks: List[Tuple[str, str, dict]] = []
    seen = set()
    for y, ad_id, item in iter_tasks(matches, args.start_year, args.end_year):
        d = digest(item)
        if d in seen:
            continue
        seen.add(d)
        if d in cache:
            continue
        tasks.append((y, ad_id, item))

    if args.limit is not None:
        tasks = tasks[: args.limit]

    call_api = get_openai_client()

    # Process in batches
    for i in range(0, len(tasks), args.batch_size):
        batch = [it[2] for it in tasks[i : i + args.batch_size]]
        batch_digests = [digest(it) for it in batch]
        messages = build_messages(batch)
        resp_text = call_api(args.model, messages, json_mode=True)
        data = parse_json(resp_text)
        results = data.get("results") or []
        # Map results by idx
        by_idx = {r.get("idx"): r for r in results if isinstance(r, dict) and "idx" in r}
        for j, d in enumerate(batch_digests):
            r = by_idx.get(j) or {}
            cache[d] = {
                "ai_context": bool(r.get("ai_context", False)),
                # accept either 'topic' or backward-compatible 'category'
                "category": r.get("topic") or r.get("category") or "",
                "confidence": r.get("confidence") if isinstance(r.get("confidence"), (int, float)) else None,
                "reason": r.get("reason") or "",
                "keyword": batch[j]["keyword"],
            }
        # Persist cache incrementally
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.5)

    # Build final validated structure aligned to input
    validated: Dict[str, Dict[str, List[dict]]] = {}
    for y, ads in matches.items():
        yi = int(y)
        if args.start_year is not None and yi < args.start_year:
            continue
        if args.end_year is not None and yi > args.end_year:
            continue
        out_ads: Dict[str, List[dict]] = {}
        for ad_id, mlist in ads.items():
            out_matches: List[dict] = []
            for m in mlist:
                item = {"keyword": m.get("keyword"), "text": m.get("text")}
                d = digest(item)
                cls = cache.get(d) or {}
                out_matches.append({
                    "keyword": m.get("keyword"),
                    "text": m.get("text"),
                    "ai_context": cls.get("ai_context"),
                    "category": cls.get("category"),
                    "confidence": cls.get("confidence"),
                    "reason": cls.get("reason"),
                })
            out_ads[ad_id] = out_matches
        validated[y] = out_ads

    OUT_PATH.write_text(json.dumps(validated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote validated results to {OUT_PATH}")


if __name__ == "__main__":
    main()
