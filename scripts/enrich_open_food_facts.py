#!/usr/bin/env python3
"""
enrich_open_food_facts.py — Open Food Facts API で既存製品データを Atom に付与

【概要】
Open Food Facts (https://world.openfoodfacts.org/) の REST API を使って
ingredient Atom に関連既存商品データを付与する（atom 内 "existing_products" キー）:

  existing_products: {
    "search_query"   : 検索クエリ
    "total_count"    : ヒット商品数
    "sample_products": 上位5件の商品サンプル
      [{
        "product_name" : 商品名
        "brand"        : ブランド名
        "categories"   : カテゴリ
        "countries"    : 販売国
        "nutriscore"   : Nutri-Score (A–E、ある場合)
        "image_url"    : 商品画像URL
        "off_url"      : Open Food Facts URL
      }]
    "top_categories" : 多い製品カテゴリ Top5
    "top_countries"  : 多い販売国 Top5
    "retrieved_at"   : 取得日時 (ISO 8601)
  }

【API】
  Open Food Facts REST API — 完全無料・APIキー不要
  https://wiki.openfoodfacts.org/API

【実行】
  python3 scripts/enrich_open_food_facts.py
  python3 scripts/enrich_open_food_facts.py --dry-run
  python3 scripts/enrich_open_food_facts.py --atom-id atom_vitamin_c
"""

import json
import time
import argparse
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from collections import Counter

ROOT = Path(__file__).parent.parent
ATOMS_FILE = ROOT / "data" / "seed-atoms" / "food-bio-atoms.json"
BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"

TARGET_TYPES = {"ingredient"}

# 検索クエリのカスタマイズ
QUERY_OVERRIDES: dict[str, str] = {
    "atom_gaba":            "GABA",
    "atom_theanine":        "theanine",
    "atom_curcumin":        "curcumin",
    "atom_magnesium":       "magnesium",
    "atom_vitamin_c":       "vitamin c",
    "atom_zinc":            "zinc supplement",
    "atom_iron":            "iron supplement",
    "atom_dha_epa":         "omega-3 DHA",
    "atom_coq10":           "coenzyme Q10",
    "atom_astaxanthin":     "astaxanthin",
    "atom_hyaluronic_acid": "hyaluronic acid",
    "atom_collagen_peptide":"collagen peptide",
    "atom_inulin":          "inulin",
    "atom_fos":             "fructooligosaccharides",
    "atom_lactobacillus":   "lactobacillus probiotic",
    "atom_bifidobacterium": "bifidobacterium",
    "atom_whey_protein":    "whey protein",
    "atom_caffeine":        "caffeine",
    "atom_green_tea":       "green tea extract",
    "atom_kurozu":          "black vinegar",
    "atom_milk":            "whole milk",
    "atom_lactose":         "lactose free",
    "atom_dietary_fiber":   "dietary fiber",
    "atom_oat_fiber":       "oat fiber",
    "atom_soy_protein":     "soy protein",
    "atom_grape_polyphenol":"grape seed extract",
    "atom_lactic_acid":     "lactic acid",
    "atom_pectin":          "pectin",
}

# 検索結果の category フィールドを除外（ノイズになる一般カテゴリ）
SKIP_CATEGORIES = {
    "Groceries", "Foodstuffs", "Foods", "Food",
    "Plant-based foods", "Unknown", "", "Miscellaneous"
}


def build_query(atom: dict) -> str:
    atom_id = atom["atom_id"]
    if atom_id in QUERY_OVERRIDES:
        return QUERY_OVERRIDES[atom_id]
    name = atom["name_en"].split("(")[0].split("/")[0].strip()
    return f"{name} supplement"


def search_products(query: str) -> Optional[dict]:
    """Open Food Facts で製品を検索する。"""
    params = urllib.parse.urlencode({
        "search_terms":  query,
        "search_simple": 1,
        "action":        "process",
        "json":          1,
        "page_size":     20,
    })
    url = f"{BASE_URL}?{params}"

    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "FormuleFuseStudio/1.0 (github.com/formula-fuse)"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 2:
                wait = 30 * (attempt + 1)
                print(f"⚠️  {e.code}, wait {wait}s...", flush=True)
                time.sleep(wait)
                continue
            return None
        except Exception:
            if attempt < 2:
                time.sleep(5)
                continue
            return None
    else:
        return None

    try:

        products = data.get("products", [])
        total_count = data.get("count", 0)

        if not products:
            return None

        # カテゴリ集計
        all_categories: list[str] = []
        all_countries: list[str] = []

        sample_products = []
        for p in products[:5]:
            name = p.get("product_name", "") or ""
            brand = p.get("brands", "") or ""
            nutriscore = p.get("nutriscore_grade", "") or ""
            image_url = p.get("image_url", "") or ""
            code = p.get("code", "") or ""

            cats_raw = p.get("categories_tags", []) or []
            cats = [c.replace("en:", "").replace("-", " ").title()
                    for c in cats_raw if c.startswith("en:")][:3]

            countries_raw = p.get("countries_tags", []) or []
            countries = [c.replace("en:", "").title()
                         for c in countries_raw if c.startswith("en:")][:3]

            all_categories.extend(cats)
            all_countries.extend(countries)

            if name:
                sample_products.append({
                    "product_name": name[:80],
                    "brand":        brand[:40],
                    "categories":   cats,
                    "countries":    countries,
                    "nutriscore":   nutriscore.upper() if nutriscore else "",
                    "image_url":    image_url[:200] if image_url else "",
                    "off_url":      f"https://world.openfoodfacts.org/product/{code}" if code else "",
                })

        # 全20件のカテゴリ・国を集計
        for p in products:
            cats_raw = p.get("categories_tags", []) or []
            cats = [c.replace("en:", "").replace("-", " ").title()
                    for c in cats_raw if c.startswith("en:")]
            all_categories.extend(cats)

            countries_raw = p.get("countries_tags", []) or []
            countries = [c.replace("en:", "").title()
                         for c in countries_raw if c.startswith("en:")]
            all_countries.extend(countries)

        top_categories = [
            cat for cat, _ in Counter(all_categories).most_common(8)
            if cat not in SKIP_CATEGORIES
        ][:5]
        top_countries = [c for c, _ in Counter(all_countries).most_common(5)]

        return {
            "search_query":    query,
            "total_count":     total_count,
            "sample_products": sample_products,
            "top_categories":  top_categories,
            "top_countries":   top_countries,
            "retrieved_at":    datetime.now(timezone.utc).isoformat(),
        }

    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Open Food Facts 既存製品データを Atom に付与")
    parser.add_argument("--dry-run", action="store_true", help="対象一覧のみ表示")
    parser.add_argument("--atom-id", help="特定の atom_id のみ処理")
    parser.add_argument("--force", action="store_true", help="既に existing_products がある Atom も再取得")
    args = parser.parse_args()

    atoms = json.loads(ATOMS_FILE.read_text(encoding="utf-8"))

    targets = [
        a for a in atoms
        if a.get("atom_type") in TARGET_TYPES
        and (args.force or "existing_products" not in a)
    ]

    if args.atom_id:
        targets = [a for a in targets if a.get("atom_id") == args.atom_id]

    print(f"🛒 Open Food Facts 対象: {len(targets)} Atom")

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

        result = search_products(query)

        if result and result["total_count"] > 0:
            atom_index[target["atom_id"]]["existing_products"] = result
            total = result["total_count"]
            cats = ", ".join(result["top_categories"][:2]) or "—"
            print(f"✅  {total:5d} products  [{cats}]")
            hit += 1
        else:
            print("—  not found")
            miss += 1

        time.sleep(0.8)

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
