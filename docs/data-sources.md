# Data Sources — Atom Intelligence Engine

## Phase 1：最初に必ず使う

### 1. USDA FoodData Central
- **用途**：食品・栄養素データ
- **取るもの**：食品名、栄養素、100gあたり成分（kcal, protein, fat, carb, fiber, minerals, vitamins）
- **Atom化**：Ingredient Atom の `usda` フィールドに付与
- **API**：https://api.nal.usda.gov/fdc/ （無料・要APIキー）
- **スクリプト**：`python3 scripts/import_usda.py --api-key YOUR_KEY`
- **状態**：✅ スクリプト完成（APIキー取得後すぐ実行可能）
- **優先度**：最優先

### 2. 日本食品標準成分表 / 文科省 食品成分データベース
- **用途**：日本市場向け食品成分
- **取るもの**：日本語食品名、栄養素、ビタミン、ミネラル、アミノ酸、脂肪酸
- **Atom化**：`data/seed-atoms/mext-atoms.json` として独立ファイルで追加
- **スクリプト**：`python3 scripts/import_mext.py <Excel ファイルパス>`
- **状態**：✅ スクリプト完成（mext.go.jp から Excel DL 後すぐ実行可能）
- **優先度**：最優先

### 3. PubChem
- **用途**：化合物データ
- **取るもの**：CID、分子式、分子量、SMILES、InChIKey
- **Atom化**：Ingredient Atom の `compound` フィールドに付与（11件済）
- **スクリプト**：`python3 scripts/enrich_pubchem.py`
- **状態**：✅ 完了（11 hit / 14 対象）
- **API**：https://pubchem.ncbi.nlm.nih.gov/rest/pug/ （完全無料・キー不要）
- **優先度**：最優先

### 4. 手入力Atom / Risk / Bond Rules
- **用途**：外部DBにないFormula Fuse固有の知識
- **取るもの**：相性、危険タグ、NG表現、Bond Rule、商品化方向
- **管理場所**：`data/seed-atoms/`
- **優先度**：最優先

---

## Phase 2：研究・発酵・酵素を強くする

### 5. FooDB
- **用途**：食品中化学成分、味、香り、健康影響
- **Atom化**：Food Compound Atom / Flavor Atom / Aroma Atom
- **注意**：商用利用ライセンス確認が必要

### 6. UniProt
- **用途**：酵素・タンパク質機能
- **Atom化**：enzyme Atom の `uniprot` フィールド（EC番号・機能・触媒反応）、microbe Atom の分類情報
- **スクリプト**：`python3 scripts/enrich_uniprot.py`
- **状態**：✅ 完了（enzyme 8件 + microbe 9件 = 17件全hit）
- **API**：https://www.uniprot.org/help/api （無料）

### 7. BRENDA
- **用途**：酵素反応、基質、生成物、pH、温度
- **Atom化**：Enzyme-Substrate Bond / Process Condition
- **注意**：ライセンス確認が必要

### 8. KEGG
- **用途**：代謝経路、反応、酵素、化合物
- **Atom化**：Pathway Atom / Reaction Bond
- **注意**：ライセンス確認が必要（商用は有料）

### 9. PubMed
- **用途**：研究論文、Evidence Map
- **Atom化**：全 Atom の `pubmed_evidence` フィールド（関連論文トップ5）
- **スクリプト**：`python3 scripts/enrich_pubmed.py [--api-key YOUR_NCBI_KEY]`
- **状態**：✅ 完了（81件中 73 hit / 8 miss）
- **API**：https://eutils.ncbi.nlm.nih.gov/entrez/eutils/ （無料）

### 10. Europe PMC
- **用途**：オープンアクセス全文、論文RAG
- **補足**：PubMedと重複するため DOI / PMID / PMCID で統合
- **API**：https://europepmc.org/RestfulWebService （無料）

---

## Phase 3：Safety Gate を強くする

### 11. EPA CompTox Chemicals Dashboard
- **用途**：化学物質毒性、物性、暴露、用途
- **Atom化**：Chemical Risk Atom / Toxicity Tag
- **API**：https://comptox.epa.gov/dashboard/api （無料）

### 12. EFSA OpenFoodTox
- **用途**：食品・飼料中化学ハザード
- **Atom化**：Toxicity Risk Tag / Safety Evidence
- **データ**：CSV一括DL可

### 13. FDA GRAS Notice Inventory
- **用途**：米国食品成分安全性・GRAS通知
- **Atom化**：全 ingredient/enzyme/microbe Atom の `gras` フィールド（status/basis/jp_status）
- **スクリプト**：`python3 scripts/enrich_fda_gras.py`
- **状態**：✅ 完了（46件全hit — 21 CFR / GRAS Notice キュレーションデータ使用）
- **データ**：https://www.fda.gov/food/gras-notice-inventory

### 14. T3DB
- **用途**：毒性化合物、毒素ターゲット
- **Atom化**：Toxic Compound Risk / Red・Black Gate

### 15. Codex / JECFA
- **用途**：国際食品安全基準、食品添加物、表示
- **Atom化**：International Safety Standard / Labeling Rule

### 16. 消費者庁 機能性表示食品届出情報
- **用途**：日本の機能性表示の参考
- **Atom化**：Claim Pattern / Functional Ingredient Atom
- **注意**：同じ表現を自動許可しない（あくまで参考）

### 17. 消費者庁 食品表示基準 / Q&A
- **用途**：日本の食品表示、アレルゲン、栄養成分表示
- **Atom化**：Japanese Labeling Rule / Allergen Rule

### 18. 厚生労働省 食薬区分
- **用途**：食品と医薬品の境界
- **Atom化**：Pharmaceutical Borderline Risk

---

## Phase 4：特許・商流を強くする

### 19–22. 特許データベース (Google Patents / J-PlatPat / Espacenet / USPTO)
- **統合スクリプト**：`python3 scripts/enrich_patents_lens.py --api-key YOUR_KEY`
- **データ元**：Lens.org API (JP+EP+US+WO を一括カバー)
- **状態**：✅ スクリプト完成（Lens.org 無料 API キー取得後すぐ実行可能）
- **Atom化**：ingredient/enzyme/microbe の `patent_landscape` フィールド（総件数・JP/US別件数・上位3件）

### 23. 原材料メーカー・商社カタログ
- **用途**：原料調達、食品グレード、MOQ、価格帯、認証、リードタイム
- **スクリプト**：`python3 scripts/enrich_suppliers.py`
- **状態**：✅ 完了（44/46 Atom にサプライヤー情報付与）
- **Atom化**：`supplier_info` フィールド（主要サプライヤー名・OEM剤形・価格帯・認証）

### 24. OEM企業データ
- **用途**：粉末、カプセル、ドリンク、発酵食品などの加工可否
- **状態**：`supplier_info.oem_forms` に含む形で実装済み
- **Atom化**：各 Atom の `supplier_info.oem_forms` フィールド

### 25. 検査機関データ
- **用途**：成分分析、微生物検査、アレルゲン検査、グルテン検査
- **Atom化**：Testing Lab Atom（未着手）

---

## Phase 5：市場・味・商品データ

### 26. FlavorDB / FlavorDB2
- **用途**：香味分子、味、香り、閾値、食品用途
- **Atom化**：Flavor Atom / Aroma Atom

### 27. Open Food Facts（FoodRepo 代替）
- **用途**：バーコード食品、既存商品数、カテゴリ、販売国
- **スクリプト**：`python3 scripts/enrich_open_food_facts.py`
- **状態**：✅ スクリプト完成・実行中（ingredient 28件対象）
- **Atom化**：`existing_products` フィールド（製品総数・Top カテゴリ・販売国・サンプル5件）
- **API**：https://world.openfoodfacts.org/ （無料・キー不要）

### 28. Amazon / 楽天 / iHerb / EC商品データ
- **用途**：競合商品、価格、レビュー、訴求
- **注意**：規約確認。公式API優先。未着手。

### 29. Google Trends
- **用途**：成分・悩み・商品キーワードの市場需要
- **スクリプト**：`python3 scripts/enrich_google_trends.py`
- **状態**：✅ スクリプト完成・実行中（ingredient+goal 46件対象、5件/バッチ）
- **Atom化**：`market_trends` フィールド（JP/US/WW 関心度・トレンド方向・ピーク月）

### 30. SNS / YouTube / TikTok / Instagramコメント
- **用途**：消費者ニーズ・悩み
- **注意**：規約・個人情報に注意。最初は手動要約。

---

## 重複データの統合方針

### 栄養素データ（USDA / MEXT）
- 日本市場では MEXT を優先
- 海外市場では USDA を優先
- `canonical_food_id` で統合
- 両方の値を `source_values` として保持

### 化合物データ（PubChem / FooDB / HMDB / ChEBI）
- PubChem CID または InChIKey を canonical key に
- 食品由来・味・香りは FooDB で補完
- 代謝文脈は HMDB で補完
- Ontology は ChEBI で補完

### 酵素データ（UniProt / BRENDA / KEGG）
- EC ナンバーを中心に統合
- タンパク質 ID は UniProt ID を保持
- 反応条件は BRENDA を優先
- 経路は KEGG を優先

### 文献データ（PubMed / Europe PMC）
- DOI を第一キー
- DOI なしの場合は PMID / PMCID
- RAG に使う本文は Europe PMC の OA 全文を優先

---

## データ品質フィールド

各 Atom のソースフィールドに以下を保持する。

```json
{
  "canonical_id": "",
  "source_id": "",
  "source_name": "",
  "source_value": null,
  "source_priority": 1,
  "source_url": "",
  "license_note": "",
  "retrieved_at": null,
  "confidence_score": null
}
```
