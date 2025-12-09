Scripts layout and usage

Folders
- AI Mentions
  - detect_ai_mentions.py — scan standoff subsets (ict-de, edu_exp_lng-de)
    - Output: Results Datasets/ai_mentions/ai_keyword_matches.json
    - CLI: --start-year, --end-year, --folders
  - detect_ai_mentions_fulltext.py — scan full ad text (adve_text_adve) from 2005+
    - Output: Results Datasets/ai_mentions/ai_keyword_matches_fulltext.json
    - CLI: --start-year, --end-year
  - analyze_ai_mentions.ipynb — standoff analysis
  - analyze_ai_mentions_fulltext.ipynb — full‑text analysis
  - validate_ai_mentions_with_gpt.py — synchronous validator using GPT (mini-batches)
  - tests/
    - cases.json — curated positive/negative strings and expected matches
    - run_keyword_tests.py — runs the matcher on cases.json and reports FPs/FNs
    - sample_matches_for_labeling.py — exports random matched snippets for manual QA (CSV)

- Exposure Calculation
  - build_exposure_assets.py — build occupation/industry lookups; enrich SJMM ads
    - Outputs: Results Datasets/exposures/*.json; Results Datasets/sjmm_ai_exposure.jsonl
  - preprocess_naics_exposure.py — prepare NAICS exposure table
  - analyze_exposure_gaps.ipynb — diagnostics

Path resolution
- Scripts compute project ROOT via Path(__file__).resolve().parents[2], so they work from their subfolders.

How to run
- Standoff mentions: python "scripts/AI Mentions/detect_ai_mentions.py" --start-year 2018
- Full‑text mentions: python "scripts/AI Mentions/detect_ai_mentions_fulltext.py" --start-year 2005 --end-year 2024
- Exposure builder: python "scripts/Exposure Calculation/build_exposure_assets.py"

Testing the matcher
- Run curated tests: python "scripts/AI Mentions/tests/run_keyword_tests.py"
- Export sample snippets for manual labeling: python "scripts/AI Mentions/tests/sample_matches_for_labeling.py"
