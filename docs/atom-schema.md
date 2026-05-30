# Atom Schema — Atom Intelligence Engine

## Atomとは

FormulaのビルディングブロックとなるデータユニットをAtomと呼ぶ。

食材・菌・酵素・条件・目的・プロセスなど、Formulaを構成するあらゆる要素がAtom。

## AtomのタイプとCategory

| atom_type | 説明 | 例 |
|---|---|---|
| `ingredient` | 原材料・食材 | 小麦タンパク、大豆タンパク、ラクトース |
| `microbe` | 微生物・菌 | 乳酸菌、酵母、麹菌 |
| `enzyme` | 酵素 | プロテアーゼ、ラクターゼ、アミラーゼ |
| `condition` | 条件（pH・温度・時間など） | pH5.5、37℃、24h発酵 |
| `goal` | 目的・効果方向 | 消化サポート、睡眠サポート |
| `process` | 加工工程 | 加熱、冷蔵保存、乾燥 |

## Atom JSONスキーマ

```json
{
  "atom_id": "atom_wheat_protein",
  "name_ja": "小麦タンパク",
  "name_en": "Wheat protein",
  "atom_type": "ingredient",
  "category": "grain_protein",
  "domain": "food_bio",
  "source_databases": ["USDA", "MEXT", "PubChem"],
  "canonical_ids": {
    "usda_fdc_id": null,
    "mext_food_id": null,
    "pubchem_cid": null,
    "inchi_key": null,
    "kegg_id": null,
    "uniprot_id": null,
    "ec_number": null
  },
  "nutrients": {
    "energy_kcal": null,
    "protein_g": null,
    "fat_g": null,
    "carbohydrate_g": null,
    "fiber_g": null,
    "sugars_g": null,
    "vitamins": {},
    "minerals": {},
    "amino_acids": {},
    "fatty_acids": {}
  },
  "usda": {
    "canonical_id": "usda:170283",
    "source_id": "170283",
    "source_name": "USDA FoodData Central",
    "source_url": "https://fdc.nal.usda.gov/fdc-app.html#/food-details/170283/nutrients",
    "source_priority": 2,
    "license_note": "CC0 1.0 Universal / public domain; cite USDA FoodData Central",
    "retrieved_at": null,
    "nutrients": {}
  },
  "mext": {
    "canonical_id": "mext:01001",
    "source_id": "01001",
    "source_name": "日本食品標準成分表（八訂）増補2023年",
    "source_url": "https://www.mext.go.jp/a_menu/syokuhinseibun/mext_00001.html",
    "source_priority": 1,
    "license_note": "出典表記: 日本食品標準成分表（八訂）増補2023年から引用（又は出典）",
    "retrieved_at": null,
    "nutrients": {}
  },
  "known_actions": ["protein_source"],
  "possible_bonds": [
    "protein_degradation",
    "fermentation",
    "baking",
    "hydrolysis"
  ],
  "risk_tags": [
    "wheat_allergen",
    "gluten_related",
    "celiac_claim_risk"
  ],
  "evidence_keywords": [
    "wheat protein hydrolysis",
    "gluten peptide reduction",
    "protease gluten"
  ],
  "regulatory_notes": [
    "Do not claim safe for wheat allergy.",
    "Do not claim safe for celiac disease without validated testing."
  ],
  "process_keywords": ["fermentation", "protease treatment", "sourdough"],
  "supplier_keywords": ["food grade wheat protein", "wheat gluten powder"],
  "default_unit": "g",
  "default_range": { "min": null, "max": null },
  "created_at": null,
  "updated_at": null
}
```

## フィールド定義

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `atom_id` | string | ✅ | 一意ID（snake_case, atom_プレフィックス） |
| `name_ja` | string | ✅ | 日本語名 |
| `name_en` | string | ✅ | 英語名 |
| `atom_type` | enum | ✅ | ingredient / microbe / enzyme / condition / goal / process |
| `category` | string | ✅ | タイプ内のサブカテゴリ |
| `domain` | string | ✅ | food_bio / pharmaceutical / chemical / defense など |
| `risk_tags` | string[] | ✅ | リスクタグ（risk-tags.json参照） |
| `possible_bonds` | string[] | ✅ | 結合可能なボンドタイプ |
| `evidence_keywords` | string[] | - | 文献検索キーワード |
| `regulatory_notes` | string[] | - | 規制上の注意（AI出力ガイド） |
| `canonical_ids` | object | - | 外部DB ID（Phase 1以降） |
| `nutrients` | object | - | 栄養素データ（Phase 1以降） |
| `usda` | object | - | USDA FoodData Central の栄養素・source metadata |
| `mext` | object | - | 日本食品標準成分表の栄養素・source metadata |

## Evidence Level 定義

| Level | 説明 |
|---|---|
| E0 | エビデンスなし |
| E1 | 理論・仮説のみ |
| E2 | in vitro（試験管内） |
| E3 | 動物実験 |
| E4 | 少数ヒト試験 |
| E5 | RCT・メタ分析 |
