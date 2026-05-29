from __future__ import annotations
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "seed-atoms"

# ── JSON キャッシュ（Atom / Bond / Risk Tag は起動時に読む） ──────────────────

_atoms_cache: Optional[list] = None
_bond_rules_cache: Optional[list] = None
_risk_tags_cache: Optional[list] = None


def _load_atoms() -> list[dict]:
    global _atoms_cache
    if _atoms_cache is not None:
        return _atoms_cache

    # Supabase から読み込む（利用可能な場合）
    sb = _get_supabase()
    if sb:
        try:
            result = sb.table("atoms").select("data").execute()
            if result.data:
                _atoms_cache = [row["data"] for row in result.data]
                return _atoms_cache
        except Exception as e:
            print(f"[DB] Supabase atoms 読み込み失敗、JSONフォールバック: {e}")

    # JSON フォールバック
    atoms: list[dict] = []
    for path in sorted(DATA_DIR.glob("*-atoms.json")):
        if path.name.startswith(".") or path.name.startswith("._"):
            continue
        with open(path, encoding="utf-8") as f:
            atoms.extend(json.load(f))
    _atoms_cache = atoms
    return _atoms_cache


def _load_bond_rules() -> list[dict]:
    global _bond_rules_cache
    if _bond_rules_cache is None:
        with open(DATA_DIR / "bond-rules.json", encoding="utf-8") as f:
            _bond_rules_cache = json.load(f)
    return _bond_rules_cache


def _load_risk_tags() -> list[dict]:
    global _risk_tags_cache
    if _risk_tags_cache is None:
        with open(DATA_DIR / "risk-tags.json", encoding="utf-8") as f:
            _risk_tags_cache = json.load(f)
    return _risk_tags_cache


# ── Atom 読み取り ──────────────────────────────────────────────────────────────

def get_all_atoms() -> list[dict]:
    return _load_atoms()


def get_atom_by_id(atom_id: str) -> Optional[dict]:
    return next((a for a in _load_atoms() if a["atom_id"] == atom_id), None)


def search_atoms(query: str) -> list[dict]:
    q = query.lower()
    return [
        a for a in _load_atoms()
        if q in a["name_ja"].lower() or q in a["name_en"].lower() or q in a["category"].lower()
    ]


def get_atoms_by_category(category: str) -> list[dict]:
    if category == "all":
        return _load_atoms()
    return [a for a in _load_atoms() if a["atom_type"] == category]


def get_all_bond_rules() -> list[dict]:
    return _load_bond_rules()


def get_all_risk_tags() -> list[dict]:
    return _load_risk_tags()


def get_risk_tag_by_id(tag_id: str) -> Optional[dict]:
    return next((t for t in _load_risk_tags() if t["tag_id"] == tag_id), None)


# ── Supabase クライアント ──────────────────────────────────────────────────────

_supabase_client = None
_supabase_available: Optional[bool] = None  # None = 未チェック
_postgres_available: Optional[bool] = None  # None = 未チェック


def _is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return (
        not value
        or "your-" in lowered
        or "placeholder" in lowered
        or "example.com" in lowered
    )


def _get_database_url() -> Optional[str]:
    url = os.getenv("DATABASE_URL", "")
    if _is_placeholder(url):
        return None
    if url.startswith(("postgresql://", "postgres://")):
        return url
    return None


@contextmanager
def _postgres_connection() -> Iterator[object]:
    global _postgres_available

    url = _get_database_url()
    if not url or _postgres_available is False:
        yield None
        return

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
    except Exception as e:
        _postgres_available = False
        print(f"[DB] PostgreSQL 接続失敗: {e} — インメモリフォールバックで動作します")
        yield None
        return

    _postgres_available = True
    try:
        yield conn
    finally:
        conn.close()


def _get_supabase():
    global _supabase_client, _supabase_available

    if _supabase_available is False:
        return None
    if _supabase_client is not None:
        return _supabase_client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_KEY", "")

    if _is_placeholder(url) or _is_placeholder(key):
        _supabase_available = False
        print("[DB] Supabase 未設定 — インメモリフォールバックで動作します")
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        _supabase_available = True
        print(f"[DB] Supabase 接続済み: {url}")
        return _supabase_client
    except Exception as e:
        _supabase_available = False
        print(f"[DB] Supabase 接続失敗: {e} — インメモリフォールバックで動作します")
        return None


# ── インメモリフォールバック ────────────────────────────────────────────────────

_formulas_store: list[dict] = []


# ── Formula CRUD ───────────────────────────────────────────────────────────────

def save_formula(formula: dict) -> dict:
    with _postgres_connection() as conn:
        if conn:
            from psycopg2.extras import Json

            row = {
                "name": formula.get("name", "Untitled"),
                "atom_ids": formula.get("atom_ids", []),
                "fused_formula": formula.get("fused_formula"),
                "ai_analysis": formula.get("ai_analysis"),
                "safety_result": formula.get("safety_result"),
            }
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into formulas
                        (name, atom_ids, fused_formula, ai_analysis, safety_result)
                    values (%s, %s, %s, %s, %s)
                    returning *
                    """,
                    (
                        row["name"],
                        Json(row["atom_ids"]),
                        Json(row["fused_formula"]),
                        Json(row["ai_analysis"]),
                        Json(row["safety_result"]),
                    ),
                )
                saved = dict(cur.fetchone())
            conn.commit()
            return _normalize_row(saved)

    sb = _get_supabase()

    if sb:
        row = {
            "name":           formula.get("name", "Untitled"),
            "atom_ids":       formula.get("atom_ids", []),
            "fused_formula":  formula.get("fused_formula"),
            "ai_analysis":    formula.get("ai_analysis"),
            "safety_result":  formula.get("safety_result"),
        }
        result = sb.table("formulas").insert(row).execute()
        return _normalize_row(result.data[0])

    # フォールバック
    formula["id"] = str(uuid.uuid4())
    formula["created_at"] = datetime.now(timezone.utc).isoformat()
    _formulas_store.append(formula)
    return formula


def get_all_formulas() -> list[dict]:
    with _postgres_connection() as conn:
        if conn:
            with conn.cursor() as cur:
                cur.execute("select * from formulas order by created_at desc")
                return [_normalize_row(dict(r)) for r in cur.fetchall()]

    sb = _get_supabase()

    if sb:
        result = sb.table("formulas").select("*").order("created_at", desc=True).execute()
        return [_normalize_row(r) for r in result.data]

    return list(reversed(_formulas_store))


def get_formula_by_id(formula_id: str) -> Optional[dict]:
    with _postgres_connection() as conn:
        if conn:
            with conn.cursor() as cur:
                cur.execute("select * from formulas where id = %s", (formula_id,))
                row = cur.fetchone()
                return _normalize_row(dict(row)) if row else None

    sb = _get_supabase()

    if sb:
        try:
            result = sb.table("formulas").select("*").eq("id", formula_id).single().execute()
            return _normalize_row(result.data)
        except Exception:
            return None

    return next((f for f in _formulas_store if f.get("id") == formula_id), None)


# ── ユーティリティ ─────────────────────────────────────────────────────────────

def _normalize_row(row: dict) -> dict:
    """Supabase レスポンスをアプリ内の dict 形式に統一する。"""
    return {
        "id":             str(row.get("id")) if row.get("id") is not None else None,
        "name":           row.get("name", ""),
        "atom_ids":       row.get("atom_ids") or [],
        "fused_formula":  row.get("fused_formula"),
        "ai_analysis":    row.get("ai_analysis"),
        "safety_result":  row.get("safety_result"),
        "created_at":     (
            row.get("created_at").isoformat()
            if hasattr(row.get("created_at"), "isoformat")
            else row.get("created_at")
        ),
    }
