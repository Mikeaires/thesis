#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MATCH_PATH = ROOT / 'Results Datasets' / 'ai_mentions' / 'ai_keyword_matches_fulltext.json'
OUT_CSV = ROOT / 'Results Datasets' / 'ai_mentions' / 'ai_fulltext_samples.csv'


def main(n: int = 200, years: tuple[int, int] | None = None) -> None:
    data = json.loads(MATCH_PATH.read_text(encoding='utf-8'))
    rows = []
    for y, ads in data.items():
        yi = int(y)
        if years and not (years[0] <= yi <= years[1]):
            continue
        for ad_id, matches in ads.items():
            for m in matches:
                rows.append((yi, ad_id, m.get('keyword',''), m.get('text','')))
    random.seed(42)
    random.shuffle(rows)
    rows = rows[:n]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSV.write_text('year,ad_id,keyword,snippet\n', encoding='utf-8')
    with OUT_CSV.open('a', encoding='utf-8') as fh:
        for y, ad, kw, snip in rows:
            snip2 = snip.replace('\n',' ').replace('"','""')
            fh.write(f'{y},{ad},{kw},"{snip2}"\n')
    print(f'wrote {len(rows)} samples to {OUT_CSV}')


if __name__ == '__main__':
    main(n=200, years=(2018, 2024))
