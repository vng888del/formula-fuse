# Formula Fuse Studio — 進捗レポート

> 自動生成: 2026-05-29 11:16 UTC
> `python3 scripts/generate_docs.py` を実行すると再生成されます。

---

## MVP 達成率

```
[████████████████████] 100%  (11/11)
```

## MVP スコープ

- ✅ **Atom を登録できる（シードデータ）**  <sub>シードJSON存在チェック</sub>
- ✅ **Atom を UI で選択できる**  <sub>AtomLibrary.tsx</sub>
- ✅ **複数 Atom を Fuse して Formula を生成できる**  <sub>fuse_engine.py</sub>
- ✅ **Formula を AI 解析できる（BYOK）**  <sub>ai_router.py</sub>
- ✅ **Risk Gate で Green/Yellow/Red/Black を判定できる**  <sub>risk_gate.py</sub>
- ✅ **AI 出力を構造化 JSON で受け取る**  <sub>AIAnalysisResult モデル</sub>
- ✅ **Formula を保存できる（永続化）**  <sub>PostgreSQL/Supabase 接続</sub>
- ✅ **Formula を保存できる（インメモリ暫定）**  <sub>_formulas_store（インメモリ）</sub>
- ✅ **Markdown レポートを出力できる**  <sub>report_generator.py</sub>
- ✅ **BYOK 方式で API キーを使う**  <sub>ApiKeyModal.tsx</sub>
- ✅ **Formula Fuse Studio の UI で動作確認できる**  <sub>page.tsx</sub>

---

## データ層

### Seed Atoms

| ファイル | 件数 |
|---|---:|
| `food-bio-atoms.json` | 153 |
| **合計** | **153** |

| atom_type | 件数 |
|---|---:|
| ingredient | 74 |
| microbe | 16 |
| enzyme | 10 |
| condition | 26 |
| goal | 27 |

### Atom エンリッチメント状況（対象タイプ別）

> ⚠️ 分母は「意味のある対象 atom_type」のみ。goal/condition は化合物・栄養データの対象外。

| フィールド | 付与済 / 対象 | カバレッジ | 完了基準 |
|---|---:|---:|---:|
| PubChem 化合物データ | 52 / 74 | 70% | ⚠️ ≥80% |
| UniProt 酵素・微生物データ | 19 / 100 | 19% | ⚠️ ≥70% |
| FDA GRAS ステータス | 74 / 74 | 100% | ✅ ≥90% |
| USDA 栄養データ | 29 / 74 | 39% | ⚠️ ≥40% |
| PubMed 文献エビデンス | 74 / 74 | 100% | ✅ ≥95% |
| サプライヤー・OEM 情報 | 74 / 74 | 100% | ✅ ≥90% |
| 特許ランドスケープ | 0 / 100 | 0% | ⬜ ≥50% |
| Google Trends 市場需要 | 62 / 74 | 84% | ✅ ≥80% |
| Open Food Facts 既存製品 | 58 / 74 | 78% | ✅ ≥70% |

### Risk Tags

| severity | 件数 |
|---|---:|
| **合計** | **26** |
| red | 5 |
| yellow | 21 |

### Bond Rules

合計 **71** ルール

| bond_type | 件数 |
|---|---:|
| functional_hypothesis | 19 |
| cofactor_synergy | 5 |
| antioxidant_synergy | 3 |
| bioavailability_enhancement | 3 |
| hydrolysis | 2 |
| fermentation_optimization | 2 |
| skin_functional_hypothesis | 2 |
| sports_functional_hypothesis | 2 |
| probiotic_immune_hypothesis | 2 |
| degradation | 1 |
| fermentation | 1 |
| gaba_synthesis | 1 |
| enzymatic_optimization | 1 |
| prebiotic_effect | 1 |
| starch_hydrolysis | 1 |
| process_interaction | 1 |
| goal_ingredient_match | 1 |
| microbial_enzyme_synergy | 1 |
| absorption_inhibition | 1 |
| antioxidant_functional_hypothesis | 1 |
| synbiotic_bond | 1 |
| probiotic_functional_hypothesis | 1 |
| biopreservation_hypothesis | 1 |
| synergistic | 1 |
| allergen_reduction | 1 |
| process_enhancement | 1 |
| formulation_bond | 1 |
| adaptogen_stack_synergy | 1 |
| immune_performance_synergy | 1 |
| longevity_nad_synergy | 1 |
| antioxidant_network_synergy | 1 |
| cognitive_energy_synergy | 1 |
| bioavailability_synergy | 1 |
| gut_health_synergy | 1 |
| polyphenol_antioxidant_network | 1 |
| nrf2_antioxidant_stack | 1 |
| sports_endurance_stack | 1 |
| multi_pathway_anti_inflammatory | 1 |
| longevity_cellular_renewal | 1 |
| mitochondrial_renewal_stack | 1 |

---

## バックエンド（FastAPI）

### API エンドポイント

合計 **17** ルート

| Method | Path | Router |
|---|---|---|
| `GET` | `/` | atoms.py |
| `GET` | `/search` | atoms.py |
| `GET` | `/category/{category}` | atoms.py |
| `GET` | `/{atom_id}` | atoms.py |
| `GET` | `/meta/bond-rules` | atoms.py |
| `GET` | `/meta/risk-tags` | atoms.py |
| `POST` | `/fuse` | formulas.py |
| `POST` | `/safety-gate` | formulas.py |
| `POST` | `/analyze` | formulas.py |
| `POST` | `/save` | formulas.py |
| `GET` | `/history` | formulas.py |
| `GET` | `/history/{formula_id}` | formulas.py |
| `GET` | `/history/{formula_id}/report` | formulas.py |
| `POST` | `/suggest` | formulas.py |
| `POST` | `/cost-estimate` | formulas.py |
| `POST` | `/dose-guide` | formulas.py |
| `POST` | `/regulatory-check` | formulas.py |

### Services

- ✅ `ai_router.py`
- ✅ `fuse_engine.py`
- ✅ `report_generator.py`
- ✅ `risk_gate.py`

### AI プロバイダー対応

- ✅ openai
- ✅ claude
- ✅ gemini

### DB / 永続化

✅ PostgreSQL/Supabase 接続済み

---

## フロントエンド（Next.js）

### Components

- ✅ `AIReactionPanel.tsx`
- ✅ `AnalyticsPanel.tsx`
- ✅ `ApiKeyModal.tsx`
- ✅ `AtomCard.tsx`
- ✅ `AtomDetailPanel.tsx`
- ✅ `AtomLibrary.tsx`
- ✅ `BondGraphPanel.tsx`
- ✅ `CostPanel.tsx`
- ✅ `DosePanel.tsx`
- ✅ `FormulaCanvas.tsx`
- ✅ `FormulaHistory.tsx`
- ✅ `FusionCanvas.tsx`
- ✅ `RegulatoryPanel.tsx`
- ✅ `SafetyBadge.tsx`
- ✅ `SuggestPanel.tsx`

### Hooks

- ✅ `useApiKey.ts`

### Lib

- ✅ `api.ts`
- ✅ `atomColors.ts`
- ✅ `utils.ts`

---

## データソース フェーズ（完了基準付き）

| Phase | 内容 | 状態 |
|---|---|---|
| 0 | 手動シード Atom | ✅ 完了 — シードJSON存在 |
| 1 | PubChem / MEXT / USDA API 連携 | ⚠️ 進行中 — PubChem 70% / USDA 39%（基準: PubChem ≥ 80%） |
| 2 | UniProt / PubMed | ✅ 完了 — PubMed 100% / UniProt 19%（基準: PubMed ≥ 95%） |
| 3 | FDA GRAS / Safety Gate 強化 | ✅ 完了 — GRAS 100%（基準: ingredient ≥ 90%） |
| 4 | サプライヤー / Lens.org 特許 | ⚠️ 進行中 — Supplier 100% / Patent 0%（基準: Supplier ≥ 90% & Patent ≥ 50%） |
| 5 | Google Trends / Open Food Facts | ✅ 完了 — Trends 84% / OpenFoodFacts 78%（基準: Trends ≥ 80% & OFF ≥ 70%） |

---

_このファイルは自動生成です。手動編集しても次回上書きされます。_
_更新: `python3 scripts/generate_docs.py`　確認: `python3 scripts/generate_docs.py --check`_

<!-- src-hash: f36dd81a27ad -->
<!-- file-hashes: {"data/seed-atoms/food-bio-atoms.json":"57fb4c1971f2","data/seed-atoms/risk-tags.json":"29e0b91b265e","data/seed-atoms/bond-rules.json":"4babe428d128","backend/app/routers/atoms.py":"909d1d265ed4","backend/app/routers/formulas.py":"c03f995c9dbd","backend/app/services/ai_router.py":"32fc17b161e8","backend/app/services/fuse_engine.py":"4db7ef8298f6","backend/app/services/risk_gate.py":"97e31176f0dd","backend/app/services/report_generator.py":"9f2ea58f680c","backend/app/db/database.py":"6b2553ce538d","docs/data-sources.md":"9bdc1c078aa5"} -->
