#!/usr/bin/env python3
"""
enrich_patents_lens.py — Lens.org API で Atom に特許ランドスケープを付与

【概要】
Lens.org (https://www.lens.org/) の REST API を使って
ingredient / enzyme / microbe Atom に特許情報を付与する（"patent_landscape" キー）:

  patent_landscape: {
    "query"         : 検索クエリ
    "total_count"   : 検索ヒット総数
    "top_patents"   : 上位3件の特許情報
      [{
        "lens_id"  : Lens ID
        "title"    : 発明名称
        "applicant": 出願人
        "year"     : 出願年
        "jurisdictions": 出願国リスト (JP/US/EP/WO 等)
        "lens_url" : Lens.org URL
      }]
    "jp_count"      : 日本特許ヒット数
    "us_count"      : 米国特許ヒット数
    "retrieved_at"  : 取得日時 (ISO 8601)
  }

【API キー取得】
  1. https://www.lens.org/lens/user/subscriptions にアクセス
  2. "Get a free API key" → 登録 → Scholarly / Patent API を選択
  3. 無料枠: 500 req/day

【実行】
  python3 scripts/enrich_patents_lens.py --api-key YOUR_KEY
  python3 scripts/enrich_patents_lens.py --api-key YOUR_KEY --dry-run
  python3 scripts/enrich_patents_lens.py --api-key YOUR_KEY --atom-id atom_gaba

【出力】
  food-bio-atoms.json を上書き（バックアップを .bak に保存）
"""

import json
import sys
import time
import argparse
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
ATOMS_FILE = ROOT / "data" / "seed-atoms" / "food-bio-atoms.json"
LENS_URL = "https://api.lens.org/patent/search"

TARGET_TYPES = {"ingredient", "enzyme", "microbe"}

# 検索クエリのカスタマイズ（atom_id → より精度の高いクエリ）
QUERY_OVERRIDES = {
    "atom_gaba":            "gamma-aminobutyric acid GABA food supplement",
    "atom_theanine":        "L-theanine food supplement composition",
    "atom_curcumin":        "curcumin turmeric food supplement bioavailability",
    "atom_dha_epa":         "DHA EPA omega-3 fatty acid food supplement",
    "atom_coq10":           "coenzyme Q10 ubiquinone food supplement",
    "atom_astaxanthin":     "astaxanthin food supplement antioxidant",
    "atom_lactase":         "lactase beta-galactosidase food enzyme",
    "atom_transglutaminase":"transglutaminase food texture protein",
    "atom_lactobacillus":   "Lactobacillus probiotic food supplement",
    "atom_bifidobacterium": "Bifidobacterium probiotic food supplement",
    "atom_natto_bacillus":  "nattokinase Bacillus subtilis natto food",
    "atom_koji":            "Aspergillus oryzae koji fermentation food",
}


def build_query(atom: dict) -> str:
    atom_id = atom["atom_id"]
    if atom_id in QUERY_OVERRIDES:
        return QUERY_OVERRIDES[atom_id]
    name = atom["name_en"].split("(")[0].split("/")[0].strip()
    atom_type = atom["atom_type"]
    suffix = {
        "ingredient": "food supplement health",
        "enzyme":     "food enzyme processing",
        "microbe":    "probiotic fermentation food",
    }.get(atom_type, "food")
    return f"{name} {suffix}"


def search_patents(query: str, api_key: str) -> Optional[dict]:
    """Lens.org でキーワード検索し、特許ランドスケープを返す。"""
    payload = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"title": query}},
                ],
                "filter": [
                    {"term": {"kind": "A"}},  # 公開特許
                ],
            }
        },
        "size": 3,
        "sort": [{"year_published": {"order": "desc"}}],
        "include": [
            "lens_id", "title", "applicants", "year_published",
            "jurisdiction", "application_reference"
        ],
        "scroll_id": None,
        "scroll": None,
    }

    # jurisdiction 別カウント用クエリ
    count_payload_jp = _build_count_query(query, "JP")
    count_payload_us = _build_count_query(query, "US")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "User-Agent":    "FormuleFuseStudio/1.0",
    }

    try:
        # メイン検索
        main_data = _post(LENS_URL, payload, headers)
        if main_data is None:
            return None

        total = main_data.get("total", {}).get("value", 0)
        hits = main_data.get("data", [])

        top_patents = []
        for hit in hits[:3]:
            applicants = [
                a.get("name", "")
                for a in hit.get("applicants", [])[:2]
                if a.get("name")
            ]
            top_patents.append({
                "lens_id":       hit.get("lens_id", ""),
                "title":         (hit.get("title") or [{}])[0].get("text", "")[:200],
                "applicant":     ", ".join(applicants),
                "year":          str(hit.get("year_published", "")),
                "jurisdictions": [hit.get("jurisdiction", "")],
                "lens_url":      f"https://www.lens.org/lens/patent/{hit.get('lens_id', '')}",
            })

        # JP/US カウント
        time.sleep(0.3)
        jp_data = _post(LENS_URL, count_payload_jp, headers)
        jp_count = jp_data.get("total", {}).get("value", 0) if jp_data else 0

        time.sleep(0.3)
        us_data = _post(LENS_URL, count_payload_us, headers)
        us_count = us_data.get("total", {}).get("value", 0) if us_data else 0

        return {
            "query":        query,
            "total_count":  total,
            "top_patents":  top_patents,
            "jp_count":     jp_count,
            "us_count":     us_count,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        return None


def _build_count_query(query: str, jurisdiction: str) -> dict:
    return {
        "query": {
            "bool": {
                "must": [
                    {"match": {"title": query}},
                ],
                "filter": [
                    {"term": {"kind": "A"}},
                    {"term": {"jurisdiction": jurisdiction}},
                ],
            }
        },
        "size": 0,
    }


def _post(url: str, payload: dict, headers: dict) -> Optional[dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("⚠️  Rate limit, wait 60s...", flush=True)
            time.sleep(60)
        return None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Lens.org 特許情報を Atom に付与")
    parser.add_argument("--api-key", required=True, help="Lens.org API キー")
    parser.add_argument("--dry-run", action="store_true", help="対象一覧のみ表示")
    parser.add_argument("--atom-id", help="特定の atom_id のみ処理")
    parser.add_argument("--force", action="store_true", help="既に patent_landscape がある Atom も再取得")
    args = parser.parse_args()

    atoms = json.loads(ATOMS_FILE.read_text(encoding="utf-8"))

    targets = [
        a for a in atoms
        if a.get("atom_type") in TARGET_TYPES
        and (args.force or "patent_landscape" not in a)
    ]

    if args.atom_id:
        targets = [a for a in targets if a.get("atom_id") == args.atom_id]

    print(f"🔍 Lens.org 特許検索対象: {len(targets)} Atom")
    print(f"   API キー: {args.api_key[:8]}...")

    if args.dry_run:
        for a in targets:
            q = build_query(a)
            print(f"  • {a['atom_id']:35s}  query: {q}")
        return

    # バックアップ
    bak = ATOMS_FILE.with_suffix(".json.bak")
    bak.write_bytes(ATOMS_FILE.read_bytes())
    print(f"💾 バックアップ: {bak.name}")

    atom_index = {a["atom_id"]: a for a in atoms}
    hit = 0
    miss = 0

    for i, target in enumerate(targets, 1):
        name = target["name_en"]
        query = build_query(target)
        print(f"[{i:>2}/{len(targets)}] {name[:35]} ...", end=" ", flush=True)

        result = search_patents(query, args.api_key)

        if result is not None:
            atom_index[target["atom_id"]]["patent_landscape"] = result
            total = result["total_count"]
            jp = result["jp_count"]
            us = result["us_count"]
            print(f"✅  total={total}  JP={jp}  US={us}")
            hit += 1
        else:
            print("—  error / not found")
            miss += 1

        # Lens.org free: 500 req/day → ~1 req/sec に留める
        time.sleep(1.2)

    # 上書き保存
    ATOMS_FILE.write_text(
        json.dumps(list(atom_index.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ 完了  hit={hit}  miss={miss}")
    print(f"💾 保存: {ATOMS_FILE}")
    print("\n次のステップ:")
    print("  python3 scripts/generate_docs.py")


if __name__ == "__main__":
    main()
