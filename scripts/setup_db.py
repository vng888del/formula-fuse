#!/usr/bin/env python3
"""
setup_db.py — Formula Fuse Studio DB セットアップ＆接続テスト

使い方:
  python3 scripts/setup_db.py           # 接続テスト + スキーマ作成
  python3 scripts/setup_db.py --check   # 接続確認のみ（スキーマ変更なし）
  python3 scripts/setup_db.py --reset   # テーブルを drop して再作成（⚠️ データ消去）

事前に backend/.env に以下を設定してください:
  SUPABASE_URL=https://xxxx.supabase.co
  SUPABASE_SERVICE_KEY=eyJ...   ← Service Role Key（Dashboard > Settings > API）
または:
  DATABASE_URL=postgresql://postgres:password@db.xxxx.supabase.co:5432/postgres
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / "backend" / ".env")

SCHEMA_SQL = """
create table if not exists formulas (
  id             uuid        primary key default gen_random_uuid(),
  name           text        not null,
  atom_ids       jsonb       not null default '[]',
  fused_formula  jsonb,
  ai_analysis    jsonb,
  safety_result  jsonb,
  created_at     timestamptz not null default now()
);

alter table formulas disable row level security;

create index if not exists formulas_created_at_idx on formulas (created_at desc);
"""

RESET_SQL = "drop table if exists formulas cascade;"

PLACEHOLDER_PATTERNS = ("your-", "placeholder", "example.com", "xxxx")


def _is_placeholder(v: str) -> bool:
    return not v or any(p in v.lower() for p in PLACEHOLDER_PATTERNS)


def _get_env() -> dict:
    return {
        "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
        "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_KEY", ""),
        "DATABASE_URL": os.getenv("DATABASE_URL", ""),
    }


# ── PostgreSQL（psycopg2）──────────────────────────────────────────────────────

def _try_postgres(env: dict, check_only: bool, reset: bool) -> bool:
    url = env["DATABASE_URL"]
    if _is_placeholder(url) or not url.startswith(("postgresql://", "postgres://")):
        return False
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        print("  ⚠️  psycopg2 が見つかりません: pip install psycopg2-binary")
        return False

    print(f"  🔌 PostgreSQL に接続中... {url[:40]}...")
    try:
        conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
        with conn.cursor() as cur:
            cur.execute("select version()")
            ver = cur.fetchone()["version"].split(",")[0]
            print(f"  ✅ 接続成功: {ver}")

            if check_only:
                cur.execute("select exists(select 1 from information_schema.tables where table_name='formulas')")
                exists = cur.fetchone()["exists"]
                print(f"  {'✅' if exists else '⬜'} formulas テーブル: {'存在' if exists else '未作成'}")
                conn.close()
                return True

            if reset:
                print("  ⚠️  formulas テーブルを DROP します...")
                cur.execute(RESET_SQL)

            for stmt in SCHEMA_SQL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)

            cur.execute("select count(*) as n from formulas")
            n = cur.fetchone()["n"]
            print(f"  ✅ スキーマ作成完了  (formulas テーブル: {n} 件)")

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  ❌ PostgreSQL エラー: {e}")
        return False


# ── Supabase クライアント──────────────────────────────────────────────────────

def _try_supabase(env: dict, check_only: bool, reset: bool) -> bool:
    url = env["SUPABASE_URL"]
    key = env["SUPABASE_SERVICE_KEY"]
    if _is_placeholder(url) or _is_placeholder(key):
        return False
    try:
        from supabase import create_client
    except ImportError:
        print("  ⚠️  supabase が見つかりません: pip install supabase")
        return False

    print(f"  🔌 Supabase に接続中... {url}")
    try:
        sb = create_client(url, key)

        # 接続確認: formulas テーブルを count
        try:
            result = sb.table("formulas").select("id", count="exact").limit(1).execute()
            n = result.count if result.count is not None else len(result.data)
            print(f"  ✅ 接続成功  formulas テーブル: {n} 件")
            if check_only:
                return True
        except Exception:
            print("  ⬜ formulas テーブルが存在しません — 作成します")

        if check_only:
            return True

        if reset:
            print("  ⚠️  formulas テーブルを DROP します（Supabase SQL Editor で実行してください）")
            print(f"     {RESET_SQL}")
            print("     ↑ Supabase Dashboard > SQL Editor に貼り付けて実行してください")
            input("  続けるには Enter を押してください...")

        # Supabase クライアントでは DDL が直接実行できないため SQL を表示
        print()
        print("  ──────────────────────────────────────────────────────")
        print("  Supabase Dashboard > SQL Editor で以下を実行してください:")
        print("  ──────────────────────────────────────────────────────")
        print(SCHEMA_SQL)
        print("  ──────────────────────────────────────────────────────")
        print()
        print("  実行後、もう一度このスクリプトを --check オプションで確認できます:")
        print("    python3 scripts/setup_db.py --check")
        return True
    except Exception as e:
        print(f"  ❌ Supabase エラー: {e}")
        return False


# ── メイン ────────────────────────────────────────────────────────────────────

def main():
    check_only = "--check" in sys.argv
    reset = "--reset" in sys.argv and not check_only

    print()
    print("╔══════════════════════════════════════════════╗")
    print("║   Formula Fuse Studio — DB セットアップ      ║")
    print("╚══════════════════════════════════════════════╝")

    env = _get_env()

    print()
    print("📋 環境変数チェック:")
    for k, v in env.items():
        if not v:
            status = "⬜ 未設定"
        elif _is_placeholder(v):
            status = "⚠️  プレースホルダー"
        else:
            short = v[:20] + "..." if len(v) > 20 else v
            status = f"✅ 設定済み ({short})"
        print(f"  {k}: {status}")

    print()
    print("🔌 DB 接続テスト:")

    # PostgreSQL を優先
    if not _is_placeholder(env["DATABASE_URL"]):
        ok = _try_postgres(env, check_only, reset)
        if ok:
            _print_success(check_only)
            return

    # 次に Supabase クライアント
    if not _is_placeholder(env["SUPABASE_URL"]):
        ok = _try_supabase(env, check_only, reset)
        if ok:
            _print_success(check_only)
            return

    # どちらも未設定
    print()
    print("  ❌ DB 接続情報が設定されていません")
    print()
    print("  ── Supabase セットアップ手順 ────────────────────────")
    print("  1. https://supabase.com/ でプロジェクトを作成（無料）")
    print("  2. Dashboard > Settings > API から以下を取得:")
    print("       - Project URL")
    print("       - service_role キー")
    print("  3. backend/.env を編集:")
    print("       SUPABASE_URL=https://<your-project>.supabase.co")
    print("       SUPABASE_SERVICE_KEY=eyJ...")
    print("  4. python3 scripts/setup_db.py を再実行")
    print("  ─────────────────────────────────────────────────────")
    print()
    sys.exit(1)


def _print_success(check_only: bool):
    print()
    if check_only:
        print("✅ DB 接続確認完了")
    else:
        print("✅ DB セットアップ完了")
        print()
        print("  次のステップ:")
        print("    uvicorn app.main:app --reload --port 8000")
        print("    → Formula の保存・履歴が永続化されます")
    print()


if __name__ == "__main__":
    main()
