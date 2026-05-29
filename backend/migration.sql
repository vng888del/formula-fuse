-- Formula Fuse Studio — Supabase migration
-- Supabase Dashboard の SQL Editor で実行してください

create table if not exists formulas (
  id          uuid        primary key default gen_random_uuid(),
  name        text        not null,
  atom_ids    jsonb       not null default '[]',
  fused_formula  jsonb,
  ai_analysis    jsonb,
  safety_result  jsonb,
  created_at  timestamptz not null default now()
);

-- バックエンドはサービスロールキーで操作するため RLS は無効のまま
-- 将来ユーザー認証を追加する場合は RLS を有効化すること
alter table formulas disable row level security;

-- インデックス（履歴一覧の高速化）
create index if not exists formulas_created_at_idx on formulas (created_at desc);

-- ── Atoms テーブル（Atom 同期用） ─────────────────────────────────────────────
create table if not exists atoms (
  atom_id       text        primary key,
  name_ja       text        not null,
  name_en       text        not null,
  atom_type     text        not null,
  category      text        not null,
  domain        text        not null default 'food_bio',
  data          jsonb       not null default '{}',
  updated_at    timestamptz not null default now()
);

alter table atoms disable row level security;

create index if not exists atoms_atom_type_idx on atoms (atom_type);
create index if not exists atoms_category_idx on atoms (category);
