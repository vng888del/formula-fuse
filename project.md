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
| Phase 1: PubChem エンリッチ | ⚠️ 52/149 (34%) |
| Phase 2: UniProt | ⚠️ 19/149 (12%) |
| Phase 2: PubMed | ⚠️ 141/149 (94%) |
| Phase 3: FDA GRAS + Safety Gate 強化 | ⚠️ 96/149 (64%) |
| Phase 4: サプライヤー情報 | ⚠️ 96/149 (64%) |
| Phase 5: Google Trends | ⚠️ 85/149 (57%) |
| Phase 5: Open Food Facts | ⚠️ 45/149 (30%) |
| **Formula 保存（Supabase DB）** | ✅ 本番稼働中 |
<!-- END:current-state -->

## Atom Counts

<!-- BEGIN:atom-counts -->
現在 **149 Atoms**（ingredient 70 / microbe 16 / enzyme 10 / condition 26 / goal 27）
<!-- END:atom-counts -->

## Bond Counts

<!-- BEGIN:bond-counts -->
現在 **63 Bond Rules**。Risk Tags **26** 件（red 5 / yellow 21）。
<!-- END:bond-counts -->

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

## Next Steps

<!-- BEGIN:next-steps -->
1. **Lens.org API キー取得** → `python3 scripts/enrich_patents_lens.py`
   - 無料登録: https://www.lens.org/
2. **Google Trends rate limit 回避**
   - 数時間待機後に `python3 scripts/enrich_google_trends.py --force` を再実行
<!-- END:next-steps -->
