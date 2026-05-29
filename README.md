# Formula Fuse Studio

**Atom Intelligence Engine** のフロントエンド。

食材・菌・酵素・条件・目的などの「Atom」を組み合わせて「Formula」を作り、AIが即座に解析・リスク判定・開発方向を返すサプリメント開発支援ツール。

---

## 機能一覧

| 機能 | 説明 |
|---|---|
| ⚛ Studio | AtomLibrary + FusionCanvas + AI解析パネル |
| 🎯 Suggest | 目的・ゴールから逆引きでAtomを提案（Reverse Formula Search） |
| 🕸 Graph | AtomのBond関係をネットワークグラフで可視化 |
| 📊 Analytics | エンリッチデータの統計・マーケットトレンド分析 |
| 💰 Cost | 原価シミュレーター（価格ティア別・バッチサイズ別試算） |
| 📐 Dose | 配合量ガイド（臨床文献ベースの推奨投与量・製剤形態） |
| 📜 Regs | 規制チェックリスト（GRAS/JP/FDA対応・JP/US/ALL切替） |
| 📋 History | フォーミュラ保存履歴 + Markdownレポート出力 |

---

## 起動方法

### 1. バックエンド（FastAPI）

```bash
cd backend
python3 -m venv .venv
pip install -r requirements.txt --target .venv/lib/python3.9/site-packages
PYTHONPATH=".venv/lib/python3.9/site-packages" python3 -m uvicorn app.main:app --reload --port 8000
```

API仕様: http://localhost:8000/docs

### 2. フロントエンド（Next.js）

> **注意（外付けSSD / ExFAT）:** `.bin`シムリンクが機能しないため `node` を直接指定

```bash
cd frontend
npm install
node node_modules/next/dist/bin/next dev --port 3000
```

ブラウザ: http://localhost:3000

---

## 使い方

### Studio（Atom選択 → Fuse → AI解析）

1. http://localhost:3000 を開く
2. 右上「🔑 API Key」から APIキーを登録（OpenAI / Claude / Gemini）
3. 左の「Atom Library」からAtomを2つ以上クリックして選択
4. 中央の「⚗️ Fuse & Analyze」ボタンを押す
5. 右の AI パネルに解析結果が表示される
6. 「💾 Formulaを保存」で保存、「📄 Markdownレポート出力」でエクスポート

### Suggest（目的 → Atom逆引き）

1. 左ナビの 🎯 をクリック
2. 目的を入力（例: 「睡眠改善」「認知機能サポート」）またはクイックゴールをタップ
3. 提案されたAtomをチェックして「X件のAtomを追加してFuse」

### Cost / Dose / Regs（右パネル切替）

Atomを選択した状態で左ナビの 💰 / 📐 / 📜 をクリックすると右パネルが切り替わる。

---

## APIキー（BYOK）

このツールはBYOK（Bring Your Own Key）方式。APIキーはブラウザのlocalStorageのみに保存され、サーバーには保持されない。

| プロバイダー | キー形式 |
|---|---|
| OpenAI | `sk-...` |
| Claude（Anthropic） | `sk-ant-...` |
| Gemini（Google） | `AIza...` |

---

## プロジェクト構成

```
formula-fuse/
├── project.md              # プロジェクト概要・進捗
├── docs/                   # 設計ドキュメント
│   ├── architecture.md     # システムアーキテクチャ
│   ├── progress.md         # 自動生成進捗レポート
│   └── ...
├── data/seed-atoms/        # 初期AtomデータJSON（153 atoms / 71 bond rules）
├── scripts/                # エンリッチ・DB同期スクリプト
├── backend/                # FastAPI（Render.comデプロイ）
│   └── app/
│       ├── routers/        # API エンドポイント
│       ├── services/       # Fuse / Risk Gate / AI Router
│       └── models/         # Pydantic モデル
└── frontend/               # Next.js（Vercelデプロイ）
    └── src/
        ├── app/page.tsx    # メインページ
        ├── components/     # 各パネルコンポーネント
        ├── lib/api.ts      # APIクライアント
        └── types/index.ts  # TypeScript型定義
```

---

## データ

- **153 Atoms**: ingredient 74 / microbe 16 / enzyme 10 / condition 26 / goal 27
- **71 Bond Rules**: 機能仮説・協力・バイオアベイラビリティ向上など
- **PubMed文献**: ingredient 100% カバー（臨床エビデンス付き）
- **サプライヤー情報**: ingredient 100%（主要・日本サプライヤー・OEM形態）
- **GRAS/安全性**: ingredient 100%
- **Google Trends**: ingredient ~83%

---

## 免責事項

このツールのAI出力は研究補助目的です。医療効果・安全性・特許性の確定的な判断ではありません。
実際の開発・販売・特許出願は必ず専門家にご相談ください。
