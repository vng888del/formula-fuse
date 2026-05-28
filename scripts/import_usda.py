#!/usr/bin/env python3
"""
import_usda.py — USDA FoodData Central API で食品栄養データを取得し Atom に付与

【概要】
USDA FoodData Central (https://fdc.nal.usda.gov/) の REST API を使って
food-bio-atoms.json の ingredient Atom に栄養データを付与する。

付与するフィールド (atom 内 "usda" キー):
  - fdc_id           : FoodData Central ID
  - description      : USDA 食品名
  - food_category    : 食品カテゴリ
  - data_type        : データタイプ (Foundation / SR Legacy / Survey 等)
  - usda_url         : FDC ページ URL
  - nutrients        : 主要栄養素の dict
      energy_kcal, protein_g, fat_g, carb_g, fiber_g, sugar_g,
      calcium_mg, iron_mg, magnesium_mg, zinc_mg,
      vitamin_c_mg, vitamin_e_mg

【API キー取得】
  https://fdc.nal.usda.gov/api-guide.html → "Get an API Key" (無料)
  取得した API キーを引数で渡す。

【実行】
  python3 scripts/import_usda.py --api-key YOUR_KEY
  python3 scripts/import_usda.py --api-key YOUR_KEY --dry-run
  python3 scripts/import_usda.py --api-key YOUR_KEY --atom-id ING_001

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
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
ATOMS_FILE = ROOT / "data" / "seed-atoms" / "food-bio-atoms.json"
BASE_URL = "https://api.nal.usda.gov/fdc/v1"

TARGET_TYPES = {"ingredient"}

# PubChem で compound 付与済みでも USDA 検索は別途行う
# （栄養データと化合物データは独立して有用）

# USDA 検索でノイズになりやすい Atom（混合物・高分子）
SKIP_KEYWORDS = {
    "Wheat protein", "Gluten", "Soy protein", "Whey protein",
    "Dietary fiber", "Grape seed proanthocyanidins (OPC)",
    "Collagen peptide", "Fructooligosaccharides (FOS)", "Pectin",
    "Hyaluronic acid", "Gamma-aminobutyric acid (GABA)",
    "L-Theanine", "Curcumin", "Coenzyme Q10 (Ubiquinone)",
    "Astaxanthin", "Lactic acid",
}

# USDA 主要栄養素の nutrientId マッピング
NUTRIENT_MAP = {
    1008: "energy_kcal",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carb_g",
    1079: "fiber_g",
    2000: "sugar_g",
    1087: "calcium_mg",
    1089: "iron_mg",
    1090: "magnesium_mg",
    1095: "zinc_mg",
    1162: "vitamin_c_mg",
    1109: "vitamin_e_mg",
}

DATA_TYPE_PRIORITY = ["Foundation", "SR Legacy", "Survey (FNDDS)", "Branded"]


def usda_search(name: str, api_key: str) -> Optional[dict]:
    """
    USDA FDC で食品名を検索し、最適なヒットの情報を返す。
    """
    params = urllib.parse.urlencode({
        "query": name,
        "dataType": "Foundation,SR Legacy",
        "pageSize": 5,
        "api_key": api_key,
    })
    url = f"{BASE_URL}/foods/search?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FormuleFuseStudio/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        foods = data.get("foods", [])
        if not foods:
            return None

        # Foundation > SR Legacy を優先
        best = None
        for priority in DATA_TYPE_PRIORITY:
            for food in foods:
                if food.get("dataType") == priority:
                    best = food
                    break
            if best:
                break
        if not best:
            best = foods[0]

        fdc_id = best["fdcId"]

        # 詳細取得（nutrient 付き）
        detail = _fetch_food_detail(fdc_id, api_key)
        if not detail:
            return None

        nutrients = _extract_nutrients(detail.get("foodNutrients", []))

        return {
            "fdc_id":        fdc_id,
            "description":   best.get("description", ""),
            "food_category": best.get("foodCategory", ""),
            "data_type":     best.get("dataType", ""),
            "usda_url":      f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{fdc_id}/nutrients",
            "nutrients":     nutrients,
        }

    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("⚠️  Rate limit hit, waiting 30s...", flush=True)
            time.sleep(30)
        return None
    except Exception:
        return None


def _fetch_food_detail(fdc_id: int, api_key: str) -> Optional[dict]:
    url = f"{BASE_URL}/food/{fdc_id}?api_key={api_key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FormuleFuseStudio/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _extract_nutrients(food_nutrients: list) -> dict:
    result = {}
    for fn in food_nutrients:
        nid = fn.get("nutrient", {}).get("id") or fn.get("nutrientId")
        if nid in NUTRIENT_MAP:
            amount = fn.get("amount") or fn.get("value")
            if amount is not None:
                result[NUTRIENT_MAP[nid]] = round(float(amount), 3)
    return result


def main():
    parser = argparse.ArgumentParser(description="USDA FDC 栄養データを Atom に付与")
    parser.add_argument("--api-key", required=True, help="USDA FDC API キー")
    parser.add_argument("--dry-run", action="store_true", help="API を叩かず対象一覧を表示")
    parser.add_argument("--atom-id", help="特定の atom_id のみ処理（デバッグ用）")
    parser.add_argument("--force", action="store_true", help="既に usda フィールドがある Atom も再取得")
    args = parser.parse_args()

    atoms = json.loads(ATOMS_FILE.read_text(encoding="utf-8"))

    targets = [
        a for a in atoms
        if a.get("atom_type") in TARGET_TYPES
        and a.get("name_en") not in SKIP_KEYWORDS
        and (args.force or "usda" not in a)
    ]

    if args.atom_id:
        targets = [a for a in targets if a.get("atom_id") == args.atom_id]

    print(f"🌾 USDA FDC エンリッチ対象: {len(targets)} Atom")

    if args.dry_run:
        for a in targets:
            print(f"  • {a['atom_id']}  {a['name_en']}")
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
        # 括弧内の補足・スラッシュ区切りを除去して検索
        search_name = name.split("(")[0].split("/")[0].strip()

        print(f"[{i:>2}/{len(targets)}] {search_name} ...", end=" ", flush=True)
        result = usda_search(search_name, args.api_key)

        if result:
            atom_index[target["atom_id"]]["usda"] = result
            nutrients = result["nutrients"]
            kcal = nutrients.get("energy_kcal", "-")
            protein = nutrients.get("protein_g", "-")
            print(f"✅  FDC={result['fdc_id']}  {result['data_type']}  {kcal}kcal  protein={protein}g")
            hit += 1
        else:
            print("—  not found")
            miss += 1

        # USDA API: 1000 req/hour の制限 → 余裕を持って 1 req/sec
        time.sleep(1.0)

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
