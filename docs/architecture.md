# Architecture — Atom Intelligence Engine

## システム概要

```
┌──────────────────────────────────────────┐
│           Formula Fuse Studio (UI)        │
│  Next.js + React + TypeScript + Tailwind  │
└────────────────────┬─────────────────────┘
                     │ REST API
┌────────────────────▼─────────────────────┐
│           Atom Intelligence Engine        │
│                 FastAPI                   │
│                                           │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ Atom DB  │  │   Fuse   │  │  Risk  │  │
│  │ Service  │  │  Engine  │  │  Gate  │  │
│  └──────────┘  └──────────┘  └────────┘  │
│                                           │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ AI Router│  │ Formula  │  │ Report │  │
│  │  (BYOK)  │  │  Graph   │  │  Gen   │  │
│  └──────────┘  └──────────┘  └────────┘  │
└────────────────────┬─────────────────────┘
                     │
┌────────────────────▼─────────────────────┐
│              Supabase                     │
│       PostgreSQL + pgvector + Auth        │
└──────────────────────────────────────────┘
```

## モジュール説明

### Atom DB Service
- Atomのベースデータを管理
- CRUD操作
- タグ・カテゴリ検索
- seed dataからの初期投入

### Fuse Engine
- 複数のAtomを受け取りFormulaを構築
- Bond Ruleを評価してAtom間の結合を解釈
- FormulaグラフをJSONで出力

### Risk Gate
- FormulaのRisk Tagを集計
- Black/Red/Yellow/Greenを判定
- 判定理由・制限アクション・代替方向を出力

### AI Router (BYOK)
- ユーザーのAPIキー（OpenAI / Claude / Gemini）を使用
- 用途別にPromptを選択
- JSON構造化出力を強制
- レート制限・エラーハンドリング

### Formula Graph
- FormulaをノードとエッジのグラフJSONで表現
- 保存・履歴管理
- 将来のReact Flowとの接続ポイント

### Report Generator
- FormulaのAI解析結果をMarkdownに変換
- Disclaimer付き出力
- エクスポート用データ整形

## APIエンドポイント（現在）

```
GET    /atoms                         # Atom一覧
GET    /atoms/{id}                    # Atom詳細
GET    /atoms/search?q=               # 検索
GET    /atoms/category/{cat}          # カテゴリ絞り込み
GET    /atoms/meta/bond-rules         # Bond Rule一覧
GET    /atoms/meta/risk-tags          # Risk Tag一覧

POST   /formula/fuse                  # Fuse実行（Bond Rule評価）
POST   /formula/safety-gate          # Safety Gate判定（Green/Yellow/Red/Black）
POST   /formula/analyze              # AI解析（BYOK: X-AI-Provider-Key ヘッダー）
POST   /formula/save                 # Formula保存
GET    /formula/history              # Formula履歴一覧
GET    /formula/history/{id}         # Formula詳細
GET    /formula/history/{id}/report  # Markdownレポート出力

POST   /formula/suggest              # 逆引き検索（目的→Atom提案）
POST   /formula/cost-estimate        # 原価シミュレーター
POST   /formula/dose-guide           # 配合量ガイド（臨床推奨量）
POST   /formula/regulatory-check     # 規制チェックリスト（JP/US/ALL）
```

## データフロー

```
User selects Atoms
     ↓
POST /formula/fuse
     ↓
Fuse Engine evaluates Bond Rules
     ↓ (fused_formula JSON)
POST /formula/safety-gate
     ↓
Risk Gate determines Green/Yellow/Red/Black
     ↓ (safety_result JSON)
POST /formula/analyze (with user's API key)
     ↓
AI Router → LLM API
     ↓ (structured JSON response)
UI renders AI Reaction Panel
     ↓
POST /formulas (save)
GET  /formulas/{id}/report (export markdown)
```

## BYOK フロー

```
User inputs API Key in UI
     ↓
Frontend sends API Key in request header: X-AI-Provider-Key
     ↓
AI Router reads key from header (never persisted server-side in MVP)
     ↓
Calls LLM API with user's key
     ↓
Returns structured JSON
```

> MVP段階ではAPIキーをDBに保存しない。フロントエンドのsession storageに保持。

## DB スキーマ（主要テーブル）

```sql
-- Atoms
atoms (
  id uuid PK,
  atom_id text UNIQUE,        -- "atom_wheat_protein"
  name_ja text,
  name_en text,
  atom_type text,             -- ingredient / microbe / enzyme / condition / goal / process
  category text,
  domain text,
  risk_tags text[],
  possible_bonds text[],
  evidence_keywords text[],
  regulatory_notes text[],
  metadata jsonb,
  created_at timestamptz
)

-- Formulas
formulas (
  id uuid PK,
  user_id uuid FK,
  name text,
  atom_ids text[],
  fused_formula jsonb,
  ai_analysis jsonb,
  safety_result jsonb,
  created_at timestamptz
)

-- Bond Rules
bond_rules (
  id uuid PK,
  bond_rule_id text UNIQUE,
  source_atom_type text,
  target_atom_type text,
  bond_type text,
  expected_result text,
  risk_level text,
  explanation text,
  metadata jsonb
)
```
