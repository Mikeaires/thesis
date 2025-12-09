#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[2]
MATCH_PATH = ROOT / "Results Datasets" / "ai_mentions" / "ai_keyword_matches_fulltext.json"
OUT_DIR = ROOT / "Results Datasets" / "ai_mentions"
OUT_DIR.mkdir(parents=True, exist_ok=True)
JSONL_PATH = OUT_DIR / "ai_mentions_batch_input.jsonl"
MANIFEST_PATH = OUT_DIR / "ai_mentions_batch_manifest.json"
VALIDATED_PATH = OUT_DIR / "ai_keyword_matches_validated.json"


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip()
            if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                v = v[1:-1]
            os.environ.setdefault(k.strip(), v)


def get_client():
    load_env()
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise SystemExit("Please install openai>=1.0: pip install openai")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY not set. Put it in .env or your environment.")
    return OpenAI()


def digest(keyword: str, snippet: str) -> str:
    h = sha256(); h.update((keyword + "\n" + snippet).encode("utf-8")); return h.hexdigest()


def iter_items(matches: Dict[str, Dict[str, List[dict]]], start_year: int | None, end_year: int | None, limit: int | None):
    seen: set[str] = set()
    count = 0
    for ys in sorted(matches.keys()):
        yi = int(ys)
        if start_year is not None and yi < start_year:
            continue
        if end_year is not None and yi > end_year:
            continue
        for ad_id, mlist in matches[ys].items():
            for m in mlist:
                kw = (m.get("keyword") or "").strip()
                sn = (m.get("text") or "").strip()
                if not kw or not sn:
                    continue
                d = digest(kw, sn)
                if d in seen:
                    continue
                seen.add(d)
                yield d, kw, sn
                count += 1
                if limit is not None and count >= limit:
                    return


def build_jsonl(matches: Dict[str, Dict[str, List[dict]]], start_year: int | None, end_year: int | None, limit: int | None) -> int:
    schema = {
        "name": "ai_context_result",
        "schema": {
            "type": "object",
            "properties": {
                "ai_context": {"type": "boolean"},
                "topic": {"type": "string"},
                "reason": {"type": "string"}
            },
            "required": ["ai_context"],
            "additionalProperties": False
        },
        "strict": True,
    }
    lines: List[str] = []
    for d, kw, sn in iter_items(matches, start_year, end_year, limit):
        body = {
            "model": "gpt-4o-mini",
            "temperature": 0,
            "response_format": {"type": "json_schema", "json_schema": schema},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You validate AI keyword matches from job ads. For each {keyword, snippet}, decide if the keyword refers to Artificial Intelligence in THIS snippet.\n"
                        "Rules:\n"
                        "- Use the snippet only; do not infer beyond it.\n"
                        "- Count as AI when it names AI methods, models, tools, roles, or products in an AI sense (e.g., ChatGPT, OpenAI, GPT-4, LLM, NLP, Computer Vision, KI-gestützt, AI-enabled, künstlich(e/er/en/em/es) Intelligenz).\n"
                        "- Not AI when letters match but meaning is different (e.g., 'KIA', 'Kinder'→'KI', 'AIM'/'AIMS', 'open air').\n"
                        "- Hyphenated/compound forms are valid (AI-enabled, KI-gestützt). Uppercase continuations forming another word are not.\n"
                        "- If context is ambiguous or insufficient, set ai_context=false and explain briefly.\n"
                        "Return JSON with: ai_context (boolean), topic (short free-text label like 'LLM'/'NLP'/'computer vision' or ''), and reason (<=120 chars)."
                    ),
                },
                {"role": "user", "content": json.dumps({"keyword": kw, "snippet": sn}, ensure_ascii=False)},
            ],
        }
        lines.append(json.dumps({
            "custom_id": d,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": body,
        }, ensure_ascii=False))
    JSONL_PATH.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def submit_batch(completion_window: str) -> dict:
    client = get_client()
    up = client.files.create(file=open(JSONL_PATH, "rb"), purpose="batch")
    batch = client.batches.create(
        input_file_id=up.id,
        endpoint="/v1/chat/completions",
        completion_window=completion_window,
    )
    info = {"input_file_id": up.id, "batch_id": batch.id, "status": batch.status}
    MANIFEST_PATH.write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def fetch_results(batch_id: str | None) -> Dict[str, dict]:
    client = get_client()
    if not batch_id:
        if not MANIFEST_PATH.exists():
            raise SystemExit("Provide --batch-id or ensure manifest exists")
        meta = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        batch_id = meta.get("batch_id")
        if not batch_id:
            raise SystemExit("batch_id missing in manifest")
    batch = client.batches.retrieve(batch_id)
    if batch.status != "completed":
        print(f"Batch {batch_id} status={batch.status}")
        raise SystemExit("Batch not completed yet")
    out_id = batch.output_file_id
    if not out_id:
        raise SystemExit("No output_file_id on batch")
    stream = client.files.content(out_id)
    data = stream.read()  # bytes
    # Parse output JSONL; build cache mapping digest->classification
    cache: Dict[str, dict] = {}
    for line in io.BytesIO(data).read().decode("utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        cid = obj.get("custom_id")
        body = (((obj.get("response") or {}).get("body")) or {})
        try:
            content = body["choices"][0]["message"]["content"]
        except Exception:
            content = "{}"
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {}
        cache[cid] = {
            "ai_context": bool(parsed.get("ai_context", False)),
            "category": parsed.get("topic") or "",
            "confidence": None,
            "reason": parsed.get("reason") or "",
        }
    return cache


def integrate_validated(cache: Dict[str, dict]) -> None:
    if not MATCH_PATH.exists():
        raise SystemExit(f"Missing matches file: {MATCH_PATH}")
    matches = json.loads(MATCH_PATH.read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, List[dict]]] = {}
    for y, ads in matches.items():
        out_ads: Dict[str, List[dict]] = {}
        for ad_id, mlist in ads.items():
            vm: List[dict] = []
            for m in mlist:
                kw = m.get("keyword")
                sn = m.get("text")
                d = digest(kw or "", sn or "")
                cls = cache.get(d) or {}
                vm.append({
                    "keyword": kw,
                    "text": sn,
                    "ai_context": cls.get("ai_context"),
                    "category": cls.get("category"),
                    "confidence": cls.get("confidence"),
                    "reason": cls.get("reason"),
                })
            out_ads[ad_id] = vm
        out[y] = out_ads
    VALIDATED_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote validated results to {VALIDATED_PATH}")


def main():
    ap = argparse.ArgumentParser(description="Build, submit, or fetch OpenAI Batch for AI mention validation")
    ap.add_argument("mode", choices=["build", "submit", "fetch", "wait"], help="Action: build JSONL, submit batch, fetch results, or wait+fetch")
    ap.add_argument("--start-year", type=int, default=None)
    ap.add_argument("--end-year", type=int, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--window", default="24h", help="Completion window for submit (default: 24h)")
    ap.add_argument("--batch-id", default=None, help="Override batch id for fetch/wait")
    ap.add_argument("--poll", type=int, default=60, help="Polling seconds for wait mode (default: 60s)")
    args = ap.parse_args()

    if args.mode == "build":
        matches = json.loads(MATCH_PATH.read_text(encoding="utf-8"))
        n = build_jsonl(matches, args.start_year, args.end_year, args.limit)
        print(f"Built JSONL with {n} unique items at {JSONL_PATH}")
        return

    if args.mode == "submit":
        if not JSONL_PATH.exists():
            raise SystemExit(f"Missing input JSONL: {JSONL_PATH}. Run 'build' first.")
        info = submit_batch(args.window)
        print(f"Submitted batch: {info}")
        return

    if args.mode == "fetch":
        cache = fetch_results(args.batch_id)
        integrate_validated(cache)
        return

    if args.mode == "wait":
        client = get_client()
        # Determine batch id
        bid = args.batch_id
        if not bid:
            if not MANIFEST_PATH.exists():
                raise SystemExit("Provide --batch-id or ensure manifest exists")
            meta = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            bid = meta.get("batch_id")
            if not bid:
                raise SystemExit("batch_id missing in manifest")
        # Poll until completion
        while True:
            b = client.batches.retrieve(bid)
            print(f"batch {bid} status={b.status}")
            if b.status == "completed":
                break
            if b.status in {"failed", "expired", "canceled"}:
                raise SystemExit(f"Batch ended with status={b.status}")
            time.sleep(args.poll)
        cache = fetch_results(bid)
        integrate_validated(cache)
        return

    # (No additional modes)


if __name__ == "__main__":
    main()
