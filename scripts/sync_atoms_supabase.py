#!/usr/bin/env python3
"""
sync_atoms_supabase.py — ローカル JSON → Supabase atoms テーブルに同期

実行:
  python3 scripts/sync_atoms_supabase.py
  python3 scripts/sync_atoms_supabase.py --dry-run
"""

import json
import os
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
ATOMS_FILE = ROOT / "data" / "seed-atoms" / "food-bio-atoms.json"

sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv
load_dotenv(ROOT / "backend" / ".env")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_KEY", "")

    if not url or not key or "your-" in url:
        print("❌ SUPABASE_URL / SUPABASE_SERVICE_KEY が未設定")
        sys.exit(1)

    from supabase import create_client
    sb = create_client(url, key)

    with open(ATOMS_FILE, encoding="utf-8") as f:
        atoms = json.load(f)

    print(f"📦 同期対象: {len(atoms)} Atom → Supabase")
    if args.dry_run:
        print("🔍 Dry-run モード（書き込みなし）")

    ok = 0
    fail = 0

    for atom in atoms:
        atom_id = atom["atom_id"]
        row = {
            "atom_id":   atom_id,
            "name_ja":   atom.get("name_ja", ""),
            "name_en":   atom.get("name_en", ""),
            "atom_type": atom.get("atom_type", ""),
            "category":  atom.get("category", ""),
            "domain":    atom.get("domain", "food_bio"),
            "data":      atom,
        }

        if args.dry_run:
            print(f"  [dry] {atom_id}")
            ok += 1
            continue

        try:
            sb.table("atoms").upsert(row, on_conflict="atom_id").execute()
            ok += 1
        except Exception as e:
            print(f"  ❌ {atom_id}: {e}")
            fail += 1

    print(f"\n✅ 完了  ok={ok}  fail={fail}")
    print("💾 Supabase atoms テーブルに同期しました")


if __name__ == "__main__":
    main()
