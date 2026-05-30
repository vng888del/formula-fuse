# Formula Fuse Studio — Project Overview

## Current State

<!-- BEGIN:current-state -->
| 区分 | 状態 |
|---|---|
| Atom 選択 UI | ✅ |
| Fuse エンジン（Bond マッチング） | ✅ |
| Risk Gate（E0–E5 + GRAS注記） | ✅ |
| AI 解析（OpenAI / Claude / Gemini） | ✅ |
| Markdown レポート出力（Phase 1–5対応） | ✅ |
| BYOK（Bring Your Own Key） | ✅ |
| AtomDetailPanel（エンリッチデータ表示） | ✅ |
| Bond 可視化（FusionCanvas） | ✅ |
| 逆引き検索 SuggestPanel | ✅ |
| 原価シミュレーター CostPanel | ✅ |
| 配合量ガイド DosePanel | ✅ |
| 規制チェックリスト RegulatoryPanel | ✅ |
| Phase 1: PubChem | ✅ 61/74 (82%) — 完了基準達成 |
| Phase 1: USDA 栄養データ | ✅ 30/74 (41%) — 完了基準達成 |
| Phase 2: UniProt | ✅ 26/26 (100%) — 完了基準達成 |
| Phase 2: PubMed | ✅ 74/74 (100%) — 完了基準達成 |
| Phase 3: FDA GRAS/Safety Gate | ✅ 74/74 (100%) — 完了基準達成 |
| Phase 4: サプライヤー情報 | ✅ 74/74 (100%) — 完了基準達成 |
| Phase 4: 特許ランドスケープ | ⬜ 0件 — 未実行 |
| Phase 5: Google Trends | ✅ 62/74 (84%) — 完了基準達成 |
| Phase 5: Open Food Facts | ✅ 58/74 (78%) — 完了基準達成 |
| **Formula 保存（Supabase DB）** | ✅ 本番稼働中 |
<!-- END:current-state -->

## Atom Counts

<!-- BEGIN:atom-counts -->
現在 **153 Atoms**（ingredient 74 / microbe 16 / enzyme 10 / condition 26 / goal 27）
<!-- END:atom-counts -->

## Bond Counts

<!-- BEGIN:bond-counts -->
現在 **71 Bond Rules**。Risk Tags **26** 件（red 5 / yellow 21）。
<!-- END:bond-counts -->

## Backend Endpoints

<!-- BEGIN:endpoints -->
| Method | Path | 説明 |
|---|---|---|
| GET | /atoms | Atom一覧 |
| GET | /atoms/search | 全文検索 |
| GET | /atoms/meta/bond-rules | Bond Rulesメタデータ |
| POST | /formula/fuse | Atom融合・Bond解析 |
| POST | /formula/safety-gate | 安全性評価 |
| POST | /formula/analyze | AI解析（BYOK） |
| POST | /formula/save | フォーミュラ保存 |
| GET | /formula/history | 保存履歴一覧 |
| GET | /formula/history/{id}/report | Markdownレポート出力 |
| POST | /formula/suggest | 逆引き検索（目的→Atom提案） |
| POST | /formula/cost-estimate | 原価シミュレーター |
| POST | /formula/dose-guide | 配合量ガイド（臨床推奨量） |
| POST | /formula/regulatory-check | 規制チェックリスト（JP/US/ALL） |
<!-- END:endpoints -->

## Frontend Nav Structure

<!-- BEGIN:nav -->
| Index | Icon | Panel | 説明 |
|---|---|---|---|
| 0 | ⚛ | Studio | AtomLibrary + FusionCanvas + AIReactionPanel |
| 1 | 🎯 | Suggest | 目的→Atom逆引き検索（全画面） |
| 2 | 🕸 | Graph | Bond関係グラフ（全画面） |
| 3 | 📊 | Analytics | エンリッチ統計・マーケット分析（全画面） |
| 4 | 💰 | Cost | 原価シミュレーター（右パネル） |
| 5 | 📐 | Dose | 配合量ガイド・臨床推奨量（右パネル） |
| 6 | 📜 | Regs | 規制チェックリスト JP/US/ALL（右パネル） |
| 7 | 📋 | History | フォーミュラ保存履歴（ドロップダウン） |
| 8 | ⚙ | Settings | APIキー設定 |
<!-- END:nav -->

## Data Phases

<!-- BEGIN:data-phases -->
| Phase | 内容 | 状態 | 詳細 |
|---|---|---|---|
| 0 | 手動シード Atom | ✅ 完了 | シードJSON存在 |
| 1 | PubChem / MEXT / USDA API 連携 | ✅ 完了 | PubChem 82% / USDA 41%（基準: PubChem ≥ 80%） |
| 2 | UniProt / PubMed | ✅ 完了 | PubMed 100% / UniProt 100%（基準: PubMed ≥ 95% & UniProt ≥ 70%） |
| 3 | FDA GRAS / Safety Gate 強化 | ✅ 完了 | GRAS 100%（基準: ingredient ≥ 90%） |
| 4 | サプライヤー / Lens.org 特許 | ⚠️ 進行中 | Supplier 100% / Patent 0%（基準: Supplier ≥ 90% & Patent ≥ 50%） |
| 5 | Google Trends / Open Food Facts | ✅ 完了 | Trends 84% / OpenFoodFacts 78%（基準: Trends ≥ 80% & OFF ≥ 70%） |
<!-- END:data-phases -->

## 完了基準（Definition of Done）

<!-- 静的セクション — generate_docs.py では上書きしない -->

| フェーズ | 対象タイプ | 完了の定義 |
|---|---|---|
| Phase 1: PubChem | ingredient | ingredient の ≥ 80% に `compound` フィールドあり |
| Phase 1: USDA | ingredient | ingredient の ≥ 40%（食品以外の素材は対象外のため低め） |
| Phase 2: PubMed | ingredient | ingredient の ≥ 95% に `pubmed_evidence` あり |
| Phase 2: UniProt | ingredient + microbe + enzyme | ≥ 70%（生体分子のみが対象） |
| Phase 3: GRAS | ingredient | ingredient の ≥ 90% に `gras` フィールドあり |
| Phase 4: Supplier | ingredient | ingredient の ≥ 90% に `supplier_info` あり |
| Phase 4: Patent | ingredient + microbe + enzyme | ≥ 50%（Lens.org APIキー取得後） |
| Phase 5: Trends | ingredient | ≥ 80% |
| Phase 5: OpenFoodFacts | ingredient | ≥ 70% |

**理由**: goal / condition atom には化合物・栄養・サプライヤーデータは不要。分母に含めると達成率が不当に下がる。

## Supabase DB 稼働確認チェックリスト

<!-- 静的セクション — generate_docs.py では上書きしない -->

本番DB稼働を「✅ 本番稼働中」と判定する条件（`backend/.env` に実URLが存在すること）。
運用上は以下を定期確認：

- [ ] `GET /health` で `db.status: "connected"` かつ `db.persistent: true`
- [ ] `GET /formula/history` が空配列以外を返す（保存済み Formula あり）
- [ ] `python3 scripts/sync_atoms_supabase.py` でAtom件数が一致
- [ ] Supabase Dashboard で `formulas` テーブルにデータあり
- [ ] Render.com の Environment Variables に `SUPABASE_URL` / `SUPABASE_KEY` 設定済み

## BYOK セキュリティ方針

<!-- 静的セクション — generate_docs.py では上書きしない -->

- APIキーは `localStorage` に永続保存（ページリロード後も維持）
- **XSSリスク**: `localStorage` はXSS攻撃で漏洩する可能性あり
  - 現状の緩和策: Next.jsのCSPヘッダー、外部スクリプト最小化
  - 今後の検討: sessionStorageオプション追加、明示削除ボタン（Settings画面）
- サーバー側でのAPIキー保存・フォールバックは**永久禁止**（"その仕様やめて"）
- `.env`はgitコミット禁止（`.gitignore`で除外済み）

## MEXT / USDA 統合方針

<!-- 静的セクション — generate_docs.py では上書きしない -->

**USDA FoodData Central**
- 既存 ingredient Atom に `usda` フィールドを**付与**（Atomは増えない）
- 一致キー: `name_en` → FoodData Central 食品名で近傍検索
- 保存フィールド: `atom.usda.fdc_id`, `atom.usda.nutrients.*`
- 対象外: 孤立サプリ素材（L-テアニン、ロジオラ等）— FDCに収録されていないため USDA カバレッジは最大 ~50% が現実的

**MEXT（日本食品標準成分表）**
- 食品素材に `mext` フィールドを付与（原則Atom追加なし）
- 対象: ingredient の中で「食品」に分類されるもの（ハーブ・発酵食品等）
- 重複防止ルール: `atom_id` が同一ならマージ、`name_ja` 一致でも `atom_type != ingredient` なら別Atomとして扱わない
- 優先ソース: `usda` > `mext`（両方ある場合はUSDAを `nutrients` のプライマリに）

## Security Constraints

<!-- BEGIN:security -->
- **BYOK必須**: APIキーはブラウザのlocalStorageにのみ保存。`X-AI-Provider-Key`ヘッダーで送信。
- サーバー側でのAPIキー保存・フォールバック **禁止**（"その仕様やめて"）。
- `.env`はgitにコミット禁止（`.gitignore`で除外済み）。
<!-- END:security -->

## Infrastructure

<!-- BEGIN:infra -->
| 区分 | サービス |
|---|---|
| フロントエンド | Vercel（Next.js） |
| バックエンド | Render.com（FastAPI） |
| DB | Supabase（PostgreSQL） |
| ファイルシステム | ExFAT SSD — `.bin`シムなし → `node node_modules/next/dist/bin/next` で起動 |
<!-- END:infra -->

## Next Steps

<!-- BEGIN:next-steps -->
1. **[P2] UniProt エンリッチ** — bio-atoms 26% → 目標 70%
   - `python3 scripts/enrich_uniprot.py --missing`
2. **[P3] Lens.org 特許エンリッチ** — 0% → 目標 50%
   - `python3 scripts/enrich_patents_lens.py`
   - 無料登録: https://www.lens.org/ (tracking: d66a994c-7f38-4312-b533-9723d4959930)
3. **[機能] フォーミュラ比較モード** — 保存済みフォーミュラのサイドバイサイド比較
4. **[機能] フォーミュラ共有** — URLシェア or QRコード生成
<!-- END:next-steps -->
