# Formula Fuse Studio

**Atom Intelligence Engine** の最初のフロントエンド。

食材・菌・酵素・条件・目的などの「Atom」を組み合わせて「Formula」を作り、AIが即座に解析・リスク判定・開発ドリームを返すツール。

---

## 起動方法

### 1. バックエンド（FastAPI）

```bash
cd backend
python3 -m venv .venv
pip install -r requirements.txt --target .venv/lib/python3.9/site-packages
PYTHONPATH=".venv/lib/python3.9/site-packages" python3 -m uvicorn app.main:app --reload --port 8000
```

API確認: http://localhost:8000/docs

### 2. フロントエンド（Next.js）

> **注意:** 外付けSSD（ExFAT形式）の場合、node_modulesが正常に動作しないことがあります。
> ローカルにコピーして起動してください。

```bash
# ローカルにコピーして起動（外付けSSDの場合）
rsync -a --exclude node_modules --exclude .next frontend/ /tmp/formula-fuse-frontend/
cd /tmp/formula-fuse-frontend
npm install
node node_modules/next/dist/bin/next dev --port 3000
```

```bash
# ローカルSSDの場合は通常通り
cd frontend
npm install
npm run dev
```

ブラウザ: http://localhost:3000

---

## 使い方

1. ブラウザで http://localhost:3000 を開く
2. 右上の「🔑 API Key設定」からAPIキーを登録（OpenAI / Claude / Gemini）
3. 左の「Atom Library」から2つ以上のAtomをクリックして選択
4. 中央の「⚗️ Fuse & Analyze」ボタンを押す
5. 右の「AI Reaction Panel」に解析結果が表示される
6. 「💾 Formulaを保存」で保存、「📄 Markdownレポート出力」でレポート取得

---

## APIキー（BYOK）

このツールはBYOK（Bring Your Own Key）方式です。

- OpenAI API Key: `sk-...`
- Claude API Key: `sk-ant-...`
- Gemini API Key: `AIza...`

APIキーはブラウザのセッションストレージのみに保存されます。サーバーには保持されません。

---

## プロジェクト構成

```
formula-fuse/
├── project.md          # プロジェクト概要
├── docs/               # 設計ドキュメント
├── data/seed-atoms/    # 初期Atomデータ
├── backend/            # FastAPI
└── frontend/           # Next.js
```

---

## 免責事項

このツールのAI出力は研究補助目的です。医療効果・安全性・特許性の確定的な判断ではありません。
実際の開発・販売・特許出願は必ず専門家にご相談ください。
