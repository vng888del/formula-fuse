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
| Phase 1: PubChem エンリッチ | ⚠️ 55/153 (35%) |
| Phase 2: UniProt | ⚠️ 19/153 (12%) |
| Phase 2: PubMed | ⚠️ 145/153 (94%) |
| Phase 3: FDA GRAS + Safety Gate 強化 | ⚠️ 100/153 (65%) |
| Phase 4: サプライヤー情報 | ⚠️ 100/153 (65%) |
| Phase 5: Google Trends | ⚠️ 89/153 (58%) |
| Phase 5: Open Food Facts | ⚠️ 58/153 (37%) |
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
| Phase | 内容 | 状態 |
|---|---|---|
| 0 | 手動シード Atom | ✅ 完了 |
| 1 | PubChem / MEXT / USDA API 連携 | ⚠️ 一部完了（PubChem のみ・MEXT未） |
| 2 | UniProt / PubMed | ✅ 完了 |
| 3 | FDA GRAS / Safety Gate 強化 | ✅ 完了 |
| 4 | サプライヤー / Lens.org 特許 | ⚠️ 一部完了（Lens.org 特許未取得） |
| 5 | Google Trends / Open Food Facts | ⚠️ 完了（Trends は rate limit あり） |
<!-- END:data-phases -->

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
1. **Open Food Facts 完了後に Supabase 再同期**
   - `python3 scripts/sync_atoms_supabase.py`
2. **Lens.org API キー取得** → `python3 scripts/enrich_patents_lens.py`
   - 無料登録: https://www.lens.org/ (トラッキングID: d66a994c-7f38-4312-b533-9723d4959930)
3. **フォーミュラ比較モード** — 保存済みフォーミュラをサイドバイサイド比較
4. **フォーミュラ共有** — URLシェア or QRコード生成
<!-- END:next-steps -->
