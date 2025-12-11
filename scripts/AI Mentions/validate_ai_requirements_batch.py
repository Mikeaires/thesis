#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import os
import time
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[2]
TEXT_DIR = ROOT / "Base Dataset" / "Data" / "699_SJMM_Data_TextualData_v10.0" / "sjmm_suf_ad_texts"
MATCH_PATH = ROOT / "Results Datasets" / "ai_mentions" / "ai_keyword_matches_fulltext.json"
OUT_DIR = ROOT / "Results Datasets" / "ai_mentions"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Default (matches-only) artifact paths for backward compatibility
JSONL_PATH = OUT_DIR / "ai_requirements_batch_input.jsonl"
MANIFEST_PATH = OUT_DIR / "ai_requirements_batch_manifest.json"
OUTPUT_JSONL = OUT_DIR / "ai_requirements_batch_output.jsonl"
RESULTS_PATH = OUT_DIR / "ai_job_requirements_simple.json"

def _span_label(start_year: int | None, end_year: int | None, for_dir: bool = False) -> str:
    if start_year is not None and end_year is not None:
        if start_year == end_year:
            return f"{start_year}"
        return f"{start_year}_{end_year}"
    if start_year is not None:
        return f"{start_year}_"
    if end_year is not None:
        return f"_{end_year}"
    return "all_years"

# Parameterized artifact paths with subfolders for organization and an aggregated results path
def get_paths(population: str, start_year: int | None, end_year: int | None,
              agg_start_year: int | None, agg_end_year: int | None,
              version: str | None = None) -> dict:
    # Version label (e.g., v3). If not provided, default to v1.
    vlabel = version or "v1"

    # Batch artifacts under: Results Datasets/ai_mentions/batches/requirements/<span>/<vlabel>/
    span = _span_label(start_year, end_year, for_dir=True)
    batch_dir = OUT_DIR / "batches" / "requirements" / span / vlabel
    batch_dir.mkdir(parents=True, exist_ok=True)

    # Aggregated results under: Results Datasets/ai_mentions/results/requirements/
    res_dir = OUT_DIR / "results" / "requirements"
    res_dir.mkdir(parents=True, exist_ok=True)

    # Aggregated span for naming the single results file we append into across runs
    agg_span = _span_label(agg_start_year if agg_start_year is not None else start_year,
                           agg_end_year if agg_end_year is not None else end_year,
                           for_dir=False)

    # Filename bases (append version label)
    base = f"ai_requirements_batch_{population}_{span}_{vlabel}"
    results_name = f"ai_job_requirements_{population}_{agg_span}_{vlabel}.json"

    return {
        "jsonl": batch_dir / f"{base}_input.jsonl",
        "manifest": batch_dir / f"{base}_manifest.json",
        "output_jsonl": batch_dir / f"{base}_output.jsonl",
        "results": res_dir / results_name,
    }


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip()
            # strip surrounding single/double quotes
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
        raise SystemExit("OPENAI_API_KEY not set. Put it in .env or the environment.")
    return OpenAI()


def build_input(population: str, start_year: int | None, end_year: int | None, limit: int | None, model: str = "gpt-4o-mini",
                agg_start_year: int | None = None, agg_end_year: int | None = None,
                version: str | None = None) -> int:
    # Determine target ads per year
    targets: Dict[int, set] = {}
    if population == "matches":
        if not MATCH_PATH.exists():
            raise SystemExit(f"Matches file not found: {MATCH_PATH}")
        matches = json.loads(MATCH_PATH.read_text(encoding="utf-8"))
        for ys, ads in matches.items():
            yi = int(ys)
            if start_year is not None and yi < start_year:
                continue
            if end_year is not None and yi > end_year:
                continue
            targets.setdefault(yi, set()).update(ads.keys())
    else:
        # all ads: we'll iterate files and include all with non-empty text
        # We'll still honor year filters via the file names found.
        years = []
        # If both provided, use range; otherwise scan available files in TEXT_DIR
        if start_year is not None and end_year is not None:
            years = list(range(start_year, end_year + 1))
        else:
            for p in TEXT_DIR.glob("ads_sjmm_*.jsonl.bz2"):
                try:
                    yi = int(p.stem.split("_")[-1])
                except Exception:
                    continue
                if start_year is not None and yi < start_year:
                    continue
                if end_year is not None and yi > end_year:
                    continue
                years.append(yi)
        for yi in sorted(set(years)):
            if (TEXT_DIR / f"ads_sjmm_{yi}.jsonl.bz2").exists():
                targets.setdefault(yi, set())  # we'll accept all ads later

    # Strict schema for v4-style output: ai_requirement takes one of "True|Maybe|False"
    schema = {
        "name": "ai_requirement_simple",
        "schema": {
            "type": "object",
            "properties": {
                "ai_requirement": {"type": "string", "enum": ["True", "Maybe", "False"]},
                "reason": {"type": "string"},
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["ai_requirement", "reason", "keywords"],
            "additionalProperties": False
        },
        "strict": True,
    }

    def system_prompt() -> str:
        # Inline v4 prompt (prompt files folder is optional and may be empty)
                return (
"""You review full job descriptions and identify if the job mentions any AI-related skills associated to the job.
These must relate to the candidate’s profile, responsibilities, or tools used in the role.
These can be requirements, nice-to-have, or something helpful for the job.

Ignore mentions of AI that only describe the company, its products or research areas, unless they are clearly
associated with the role, its requirements or the candidate profile.

Your task is to assign ONE of the following values to a single field "ai_requirement":

- "True"  - clear AI/ML skills or responsibilities are required / desired for the role
- "Maybe" - skills that sometimes involve AI but are not necessarily AI-specific and can also be done without AI.
- "False" - no relevant AI or AI-related requirement.

-----------------------
RULES FOR "True"
-----------------------

Assign ai_requirement = "True" ONLY if the job text contains at least one EXPLICIT AI/ML reference connected
to the candidate’s skills, tools, or responsibilities, for example:

- artificial intelligence, AI
- machine learning, ML
- deep learning, neural networks
- data science (as a main skill or role)
- natural language processing, NLP, sentiment analysis
- computer vision, image processing, image recognition
- speech recognition
- anomaly detection
- forecasting models
- predictive maintenance
- generative AI, LLMs, large language models, ChatGPT, GPT
- recommendation systems, recommender systems
- AI agents, autonomous agents
- TensorFlow, PyTorch, scikit-learn, Keras (when used for ML/AI)
- AI governance, AI ethics, AI product management, AI strategy

Assign ai_requirement = "True" if ANY of the following applies:
- The job explicitly requires AI-related skills or experience (as ins the examples above).
- The job states that familiarity or interest in AI is advantageous, desirable, or a plus.
- The job explicitly requires familiarity or experience with AI/ML concepts, technologies, or applications
  (as in the examples above) in the context of the candidate’s skills, tools, or responsibilities.
- The job describes tasks that directly involve the use, management, or understanding of AI systems
  (e.g., AI governance, AI ethics, AI product management, AI strategy, building or deploying ML/AI models).

If no explicit AI/ML term appears in the job text, NEVER assign "True".

-----------------------
RULES FOR "Maybe"
-----------------------

"Maybe" is ONLY for skills or technologies that are OFTEN AI/ML but are not necessarily AI,
AND are directly part of the job requirements or the candidate’s profile or responsibilities.

Assign ai_requirement = "Maybe" if ALL of the following are true:
- None of the "True" conditions above apply (no explicit AI/ML requirement).
- The job requires at least one concept that might be AI but can also be done without it, as teh examples from this list (examples, not exhaustive):

  - data mining
  - robotics, robot control
  - general signal processing
  - general automation
  - general optimization 
  - predictive analytics
  - RPA / Robotic Process Automation (without explicit AI/ML/NLP/computer vision)

- These skills/concepts are clearly part of the candidate’s profile, responsibilities, or tools used in the role.

Important Rule:
If the job only has requirements that might be AI but are not necessarily AI, and these requirements match the
examples above, the classification must be ai_requirement = "Maybe".

-----------------------
RULES FOR "False"
-----------------------

Assign ai_requirement = "False" if:
- None of the "True" conditions apply (no explicit AI/ML mention), AND
- None of the AI-adjacent "Maybe" conditions apply (no concepts from the "Maybe" list), AND
- AI/ML or AI-adjacent skills are not clearly connected to the candidate’s skills, requirements, tools,
  or responsibilities.

Do NOT treat the following as AI or maybe AI. If ONLY these appear (and no explicit AI/ML terms
and no concepts taht are maybe AI from the "Maybe" list), then the classification must be "False":

- big data, data analysis, data analytics, business intelligence, reporting, dashboards
- statistics, econometrics, mathematics
- SQL, relational databases, data warehouses, ETL, data engineering
- cloud, cloud computing (e.g. AWS, Azure, GCP) without explicit AI/ML services
- IoT / Internet of Things (without explicit AI/ML use)
- digitalization, digitization, digital transformation, Industry 4.0 (without explicit AI/ML)
- general automation or scripting (e.g. Excel macros, VBA, Python scripting) without AI context
- generic buzzwords like “innovative technologies”, “cutting-edge digital solutions” without clear AI content

If a job only mentions these excluded terms, do NOT assign "True" or "Maybe". Assign "False".

-----------------------
OUTPUT FORMAT
-----------------------

Return JSON with fields:
- ai_requirement: one of "True", "Maybe", or "False"
- reason: a very short justification (<=150 chars)
- keywords: a list of relevant AI or AI-adjacent keywords EXACTLY IN TEH WAY TAHT TEHY ARE WRITTEN IN TEH TEXT (use [] if none). If the classificatino is "True", add only the keywords that are really AI specific as described in the "Rules for True"."""


        )


    paths = get_paths(population, start_year, end_year, agg_start_year, agg_end_year, version=version)
    paths["jsonl"].parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with paths["jsonl"].open("w", encoding="utf-8") as out:
        for year in sorted(targets.keys()):
            p = TEXT_DIR / f"ads_sjmm_{year}.jsonl.bz2"
            if not p.exists():
                continue
            # Build ad_id -> full text index only for targeted ads
            wanted = targets[year]
            idx: Dict[str, str] = {}
            import bz2
            with bz2.open(p, "rt", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    ad = obj.get("adve_iden_adve")
                    txt = obj.get("adve_text_adve") or ""
                    if not isinstance(txt, str) or not txt:
                        continue
                    if population == "matches":
                        if ad in wanted:
                            idx[ad] = txt
                    else:
                        idx[ad] = txt
            # Emit records
            ad_ids = sorted(idx.keys()) if population == "matches" else sorted(idx.keys())
            for ad_id in ad_ids:
                if limit is not None and written >= limit:
                    return written
                txt = idx.get(ad_id)
                if not txt:
                    continue
                body = {
                    "model": model,
                    "response_format": {"type": "json_schema", "json_schema": schema},
                    "messages": [
                        {"role": "system", "content": system_prompt()},
                        {"role": "user", "content": json.dumps({"ad_id": ad_id, "text": txt}, ensure_ascii=False)},
                    ],
                }
                custom_id = ad_id if population == "matches" else f"{year}|{ad_id}"
                rec = {
                    "custom_id": custom_id,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": body,
                }
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1
    return written


def submit(window: str, population: str, start_year: int | None, end_year: int | None,
           agg_start_year: int | None = None, agg_end_year: int | None = None,
           version: str | None = None) -> dict:
    client = get_client()
    paths = get_paths(population, start_year, end_year, agg_start_year, agg_end_year, version=version)
    up = client.files.create(file=open(paths["jsonl"], "rb"), purpose="batch")
    batch = client.batches.create(input_file_id=up.id, endpoint="/v1/chat/completions", completion_window=window)
    info = {"input_file_id": up.id, "batch_id": batch.id, "status": batch.status}
    paths["manifest"].write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def fetch(batch_id: str | None, population: str, start_year: int | None, end_year: int | None,
          agg_start_year: int | None = None, agg_end_year: int | None = None,
          version: str | None = None) -> List[dict]:
    client = get_client()
    paths = get_paths(population, start_year, end_year, agg_start_year, agg_end_year, version=version)
    if not batch_id:
        if not paths["manifest"].exists():
            raise SystemExit("Provide --batch-id or ensure manifest exists")
        meta = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        batch_id = meta.get("batch_id")
        if not batch_id:
            raise SystemExit("batch_id missing in manifest")
    b = client.batches.retrieve(batch_id)
    if b.status != "completed":
        print(f"batch {batch_id} status={b.status}")
        raise SystemExit("Batch not completed yet")
    out_id = b.output_file_id
    # Sometimes output_file_id lags behind status=completed; wait briefly
    attempts = 0
    # wait up to ~10 minutes for output_file_id
    while not out_id and attempts < 200:
        time.sleep(3)
        b = client.batches.retrieve(batch_id)
        out_id = b.output_file_id
        attempts += 1
    if not out_id:
        raise SystemExit("No output_file_id")
    data = client.files.content(out_id).read()
    # Persist raw output for traceability
    try:
        paths["output_jsonl"].write_bytes(data)
    except Exception:
        pass
    # Build list of results; when population==all, custom_id encodes year|ad_id
    results: List[dict] = []
    for line in io.BytesIO(data).read().decode("utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        cid = obj.get("custom_id") or ""
        year = None
        ad_id = cid
        if population == "all" and "|" in cid:
            try:
                y_str, ad_id = cid.split("|", 1)
                year = int(y_str)
            except Exception:
                year = None
        body = (((obj.get("response") or {}).get("body")) or {})
        try:
            content = body["choices"][0]["message"]["content"]
        except Exception:
            content = "{}"
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {}
        # normalize keywords if present
        kws_raw = parsed.get("keywords")
        keywords: List[str] = []
        if isinstance(kws_raw, list):
            for k in kws_raw:
                if isinstance(k, str):
                    t = k.strip()
                    if t and t not in keywords:
                        keywords.append(t)
        # ai_requirement now string: 'True'|'Maybe'|'False' (accept booleans/backward-compat)
        ar = parsed.get("ai_requirement")
        if isinstance(ar, bool):
            ar = "True" if ar else "False"
        elif isinstance(ar, str):
            val = ar.strip()
            if val.lower() in ("true", "t", "yes"): ar = "True"
            elif val.lower() in ("false", "f", "no"): ar = "False"
            elif val.lower() == "maybe": ar = "Maybe"
            else: ar = val
        else:
            ar = "False"
        if ar not in ("True", "Maybe", "False"):
            ar = "False"
        results.append({
            "ad_id": ad_id,
            "year": year,
            "ai_requirement": ar,
            "reason": (parsed.get("reason") or "")[:150],
            "keywords": keywords,
        })
    return results


def integrate(results: List[dict], population: str, start_year: int | None, end_year: int | None,
              agg_start_year: int | None = None, agg_end_year: int | None = None,
              version: str | None = None) -> None:
    paths = get_paths(population, start_year, end_year, agg_start_year, agg_end_year, version=version)
    # Load existing aggregated results (to append/merge)
    if paths["results"].exists():
        try:
            out: Dict[str, Dict[str, dict]] = json.loads(paths["results"].read_text(encoding="utf-8"))
        except Exception:
            out = {}
    else:
        out = {}
    if population == "matches":
        if not MATCH_PATH.exists():
            raise SystemExit(f"Missing matches: {MATCH_PATH}")
        matches = json.loads(MATCH_PATH.read_text(encoding="utf-8"))
        # Build quick index ad_id -> result
        r_index: Dict[str, dict] = {}
        for r in results:
            aid = r.get("ad_id")
            if aid:
                r_index[aid] = r
        for ys, ads in matches.items():
            yi = int(ys)
            if start_year is not None and yi < start_year:
                continue
            if end_year is not None and yi > end_year:
                continue
            out_ads: Dict[str, dict] = out.get(ys, {})
            for ad_id in ads.keys():
                r = r_index.get(ad_id)
                if r:
                    out_ads[ad_id] = {
                        "ai_requirement": r.get("ai_requirement") or "False",
                        "reason": r.get("reason") or "",
                        "keywords": r.get("keywords", []),
                    }
            if out_ads:
                out[ys] = out_ads
    else:
        # Group by explicit years provided in results
        for r in results:
            y = r.get("year")
            ad_id = r.get("ad_id")
            if y is None or not ad_id:
                continue
            if start_year is not None and y < start_year:
                continue
            if end_year is not None and y > end_year:
                continue
            ys = str(y)
            out.setdefault(ys, {})[ad_id] = {
                "ai_requirement": r.get("ai_requirement") or "False",
                "reason": r.get("reason") or "",
                "keywords": r.get("keywords", []),
            }
    paths["results"].write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote results to {paths['results']}")


def main():
    ap = argparse.ArgumentParser(description="OpenAI Batch: classify AI skill requirements (full ad text)")
    ap.add_argument("mode", choices=["build", "submit", "wait", "fetch"], help="Action to perform")
    ap.add_argument("--population", choices=["matches", "all"], default="matches", help="Which population to evaluate (matches=ads with AI mentions; all=every ad)")
    ap.add_argument("--start-year", type=int, default=None)
    ap.add_argument("--end-year", type=int, default=None)
    ap.add_argument("--agg-start-year", type=int, default=None, help="Aggregate results file start year (for appending across many runs)")
    ap.add_argument("--agg-end-year", type=int, default=None, help="Aggregate results file end year (for appending across many runs)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--version", default="v1", help="Version label for file organization and suffix (e.g., v3)")
    ap.add_argument("--model", default="gpt-4o-mini", help="Model to use in batch requests (default: gpt-4o-mini)")
    ap.add_argument("--window", default="24h", help="Completion window for submit/wait")
    ap.add_argument("--batch-id", default=None)
    ap.add_argument("--poll", type=int, default=3)
    args = ap.parse_args()

    if args.mode == "build":
        n = build_input(args.population, args.start_year, args.end_year, args.limit, model=args.model,
                        agg_start_year=args.agg_start_year, agg_end_year=args.agg_end_year, version=args.version)
        p = get_paths(args.population, args.start_year, args.end_year, args.agg_start_year, args.agg_end_year, version=args.version)["jsonl"]
        print(f"Built requirements JSONL with {n} requests at {p}")
        return

    if args.mode == "submit":
        p = get_paths(args.population, args.start_year, args.end_year, args.agg_start_year, args.agg_end_year, version=args.version)["jsonl"]
        if not p.exists():
            raise SystemExit(f"Missing input JSONL: {p}. Run 'build' first.")
        info = submit(args.window, args.population, args.start_year, args.end_year,
                      agg_start_year=args.agg_start_year, agg_end_year=args.agg_end_year, version=args.version)
        print(f"Submitted batch: {info}")
        return

    if args.mode == "wait":
        client = get_client()
        bid = args.batch_id
        if not bid:
            m = get_paths(args.population, args.start_year, args.end_year, args.agg_start_year, args.agg_end_year, version=args.version)["manifest"]
            if not m.exists():
                raise SystemExit("Provide --batch-id or ensure manifest exists")
            meta = json.loads(m.read_text(encoding="utf-8"))
            bid = meta.get("batch_id")
            if not bid:
                raise SystemExit("batch_id missing in manifest")
        while True:
            b = client.batches.retrieve(bid)
            print(f"batch {bid} status={b.status}")
            if b.status == "completed":
                break
            if b.status in {"failed", "expired", "canceled"}:
                raise SystemExit(f"Batch ended with status={b.status}")
            time.sleep(args.poll)
        # on completion, fall through to fetch
        args.batch_id = bid

    if args.mode == "fetch" or (args.mode == "wait" and args.batch_id):
        results = fetch(args.batch_id, args.population, args.start_year, args.end_year,
                        agg_start_year=args.agg_start_year, agg_end_year=args.agg_end_year, version=args.version)
        integrate(results, args.population, args.start_year, args.end_year,
                  agg_start_year=args.agg_start_year, agg_end_year=args.agg_end_year, version=args.version)
        return


if __name__ == "__main__":
    main()
