# Formula Fuse Studio

> **Atom Intelligence Engine** — 食品・バイオ開発 AI ツール。
> 食材・菌・酵素・条件・目的などの「Atom」を組み合わせて「Formula」を作り、
> AI が即座に解析・リスク判定・開発ドリームを返す。

```
Combination → Calculation → Invention
```

---

## ビジョン

食品・健康食品・発酵・バイオ・素材開発の担当者が、直感的に原材料の組み合わせを試し、
AI が「何が起こるか」「どんなリスクがあるか」「どう商品化できるか」を即座に返す。
研究・開発・特許・OEM の入口となる「開発ドリーム変換エンジン」。

**ターゲットユーザー**
- 食品・健康食品・発酵・バイオ・素材メーカーの開発担当者
- スタートアップ・個人開発者・研究者
- OEM・原材料調達担当者

---

## 現在の状態

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
| Phase 1: PubChem エンリッチ | ⚠️ 13/82 (15%) |
| Phase 2: UniProt | ⚠️ 17/82 (20%) |
| Phase 2: PubMed | ⚠️ 74/82 (90%) |
| Phase 3: FDA GRAS + Safety Gate 強化 | ⚠️ 46/82 (56%) |
| Phase 4: サプライヤー情報 | ⚠️ 44/82 (53%) |
| Phase 5: Google Trends | ⚠️ 46/82 (56%) |
| Phase 5: Open Food Facts | ⚠️ 27/82 (32%) |
| **Formula 保存（Supabase DB）** | ✅ 本番稼働中 |
<!-- END:current-state -->

詳細は [`docs/progress.md`](docs/progress.md) を参照（`python3 scripts/generate_docs.py` で最新化）。

---

## コアコンセプト

### Atom
組み合わせの最小単位。以下の 5 タイプがある。

| type | 説明 | 例 |
|---|---|---|
| `ingredient` | 原材料・成分 | 小麦タンパク、乳酸菌、イヌリン |
| `microbe` | 微生物 | 乳酸菌、麹菌、酵母 |
| `enzyme` | 酵素 | プロテアーゼ、ラクターゼ |
| `condition` | 加工・環境条件 | pH 5.5、37℃、48h発酵 |
| `goal` | 開発目的 | 消化サポート、GABA発酵、美肌 |

<!-- BEGIN:atom-counts -->
現在 **82 Atoms**（ingredient 29 / microbe 9 / enzyme 8 / condition 19 / goal 17）
<!-- END:atom-counts -->

各 Atom には Phase 1–5 のエンリッチデータが付与される（PubChem・UniProt・GRAS・PubMed・サプライヤー・特許・Google Trends・Open Food Facts）。

### Formula
2 つ以上の Atom を組み合わせた「仮説レシピ」。
Fuse Engine が Bond Rules に照合し、どんな反応が起こりうるかを計算する。

### Bond Rules
「どの Atom タイプの組み合わせで何が起きるか」を定義したルール群。

<!-- BEGIN:bond-counts -->
現在 **18 Bond Rules**。Risk Tags **26** 件（red 5 / yellow 21）。
<!-- END:bond-counts -->

### Risk Gate
Formula の全 risk_tags を評価し、4 段階で判定する。
Phase 3 拡張で E0–E5 エビデンスレベル・GRAS 注記・Atom 別安全メモを追加。

| 判定 | 意味 | 制限 |
|---|---|---|
| 🟢 Green | リスクタグなし | 全アクション可 |
| 🟡 Yellow | 要注意タグあり | 全アクション可・専門家確認推奨 |
| 🔴 Red | 要専門家確認タグあり | 原材料調達・商品化方向を非表示 |
| ⛔ Black | 高リスクタグあり | 全アクション停止 |

### AI 解析（BYOK）
ユーザー自身の API キーを使い、以下の 3 プロバイダーから選択して解析する。
キーはブラウザのセッションストレージのみに保持。サーバーには渡らない。

| プロバイダー | デフォルトモデル |
|---|---|
| OpenAI | gpt-4o-mini |
| Claude | claude-haiku-4-5-20251001 |
| Gemini | gemini-1.5-flash |

---

## アーキテクチャ

```
[Browser]
  ├── AtomLibrary         ← Atom 一覧・選択・GRAS バッジ・PubMed 件数
  ├── AtomDetailPanel     ← Atom エンリッチ詳細（PubChem/UniProt/Supplier/Trends 等）
  ├── FusionCanvas        ← 選択 Atom 表示・Bond 可視化（リスク色）・Fuse 実行
  ├── AIReactionPanel     ← AI 解析結果・Safety Gate・GRAS 注記・Next Actions
  ├── FormulaHistory      ← 過去 Formula 一覧（安全性カラー）
  └── ApiKeyModal         ← BYOK 設定（SessionStorage）
         │
         │ HTTP / fetch
         ▼
[FastAPI :8000]
  ├── GET  /atoms                      ← Atom 一覧（Phase 1–5 エンリッチデータ含む）
  ├── GET  /atoms/search               ← 検索
  ├── GET  /atoms/category/{cat}       ← カテゴリ絞込
  ├── GET  /atoms/meta/bond-rules      ← Bond Rule 一覧
  ├── GET  /atoms/meta/risk-tags       ← Risk Tag 一覧
  ├── POST /formula/fuse               ← Bond マッチング
  ├── POST /formula/safety-gate        ← Risk Gate 判定（E0–E5・GRAS注記付き）
  ├── POST /formula/analyze            ← AI 解析（BYOK・Phase 1–5 コンテキスト）
  ├── POST /formula/save               ← Formula 保存
  ├── GET  /formula/history            ← 履歴一覧
  ├── GET  /formula/history/{id}       ← 個別取得
  └── GET  /formula/history/{id}/report ← Markdown レポート（Phase 1–5 セクション付き）
         │
  ┌──────┴──────────────────────────────────────────┐
  │ Services                                        │
  │  fuse_engine.py      Bond 計算                  │
  │  risk_gate.py        リスク判定（E0–E5 対応）    │
  │  ai_router.py        LLM 呼び出し + エンリッチ   │
  │  report_generator.py MD 生成（10 セクション）   │
  └──────┬──────────────────────────────────────────┘
         │
  [DB / Data]
  ├── data/seed-atoms/food-bio-atoms.json   ← Atom マスタ（82件・Phase 1–5付き）
  ├── data/seed-atoms/risk-tags.json        ← Risk Tag 定義（26件）
  ├── data/seed-atoms/bond-rules.json       ← Bond Rules（18件）
  └── Supabase (PostgreSQL)                 ← ✅ Formula 永続化（本番稼働中）
```

---

## 技術スタック

| レイヤー | 技術 |
|---|---|
| Frontend | Next.js 16 + React 19 + TypeScript + Tailwind CSS v4 |
| Backend | FastAPI (Python 3.9+) |
| AI | BYOK (OpenAI / Claude / Gemini) |
| Data（Atom） | JSON ファイル（Phase 1–5 エンリッチ付き） |
| Data（Formula） | Supabase (PostgreSQL) ✅ 本番稼働中 |
| Auth（予定） | Supabase Auth |

---

## ディレクトリ構成

```
formula-fuse/
├── project.md                 ← このファイル（全体概要・動的セクション自動更新）
├── docs/
│   ├── progress.md            ← 自動生成・進捗レポート
│   ├── data-sources.md        ← データソース計画（Phase 1〜5）
│   ├── architecture.md        ← アーキテクチャ詳細
│   ├── atom-schema.md         ← Atom スキーマ定義
│   ├── safety-gate.md         ← Risk Gate 設計
│   └── prompts.md             ← AI プロンプト設計
├── scripts/
│   ├── generate_docs.py       ← progress.md + project.md 動的セクション更新
│   ├── import_usda.py         ← USDA FoodData Central エンリッチ（要APIキー）
│   ├── enrich_uniprot.py      ← UniProt REST API エンリッチ ✅
│   ├── enrich_pubmed.py       ← NCBI PubMed eUtils エンリッチ ✅
│   ├── enrich_fda_gras.py     ← FDA GRAS キュレーション ✅
│   ├── enrich_suppliers.py    ← サプライヤー情報キュレーション ✅
│   ├── enrich_patents_lens.py ← Lens.org 特許（要APIキー）
│   ├── enrich_google_trends.py ← Google Trends（⚠️ rate limit）
│   └── enrich_open_food_facts.py ← Open Food Facts ✅
├── data/seed-atoms/
│   ├── food-bio-atoms.json    ← Atom マスタ（82件・Phase 1–5 エンリッチ付き）
│   ├── risk-tags.json         ← Risk Tag 定義（26件）
│   └── bond-rules.json        ← Bond Rules（18件）
├── backend/
│   └── app/
│       ├── main.py
│       ├── models/            ← Pydantic モデル
│       ├── routers/           ← API ルーター
│       ├── services/          ← ビジネスロジック
│       └── db/                ← データアクセス層
└── frontend/
    └── src/
        ├── app/               ← Next.js ページ
        ├── components/        ← UI コンポーネント（AtomCard, AtomDetailPanel 等）
        ├── hooks/             ← カスタムフック
        ├── lib/               ← API クライアント・ユーティリティ
        └── types/             ← TypeScript 型定義（Phase 1–5 型付き）
```

---

## 起動方法

### バックエンド（FastAPI）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API ドキュメント: http://localhost:8000/docs

### フロントエンド（Next.js）

```bash
# 外付けSSD（ExFAT）の場合はローカルにコピーして起動
rsync -a --exclude node_modules --exclude .next frontend/ /tmp/formula-fuse-frontend/
cd /tmp/formula-fuse-frontend
npm install
node node_modules/next/dist/bin/next dev --port 3000
```

ブラウザ: http://localhost:3000

### ドキュメント更新

```bash
# docs/progress.md + project.md の動的セクションを両方更新
python3 scripts/generate_docs.py

# 古くなっていないか確認
python3 scripts/generate_docs.py --check
```

---

## データソース フェーズ計画

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

詳細: [`docs/data-sources.md`](docs/data-sources.md)

---

## 次に着手すること

<!-- BEGIN:next-steps -->
1. **Lens.org API キー取得** → `python3 scripts/enrich_patents_lens.py`
   - 無料登録: https://www.lens.org/
2. **Google Trends rate limit 回避**
   - 数時間待機後に `python3 scripts/enrich_google_trends.py --force` を再実行
<!-- END:next-steps -->

---

## 免責事項

このツールの AI 出力は研究補助目的です。
医療効果・安全性・特許性の確定的な判断ではありません。
実際の開発・販売・特許出願・規制対応は必ず専門家にご相談ください。
