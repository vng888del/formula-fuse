#!/usr/bin/env python3
"""
enrich_pubchem.py — PubChem PUG REST API で Atom に化合物データを付与

【概要】
data/seed-atoms/food-bio-atoms.json の ingredient / enzyme Atom を対象に
PubChem を検索し、以下を付与する:
  - pubchem_cid     : PubChem Compound ID
  - molecular_formula: 分子式
  - molecular_weight : 分子量 (g/mol)
  - smiles           : 簡易 SMILES (isomeric)
  - inchikey         : InChIKey
  - pubchem_url      : PubChem ページ URL

API キー不要・完全無料。

【実行】
python3 scripts/enrich_pubchem.py              # 全対象を処理
python3 scripts/enrich_pubchem.py --dry-run    # API を叩かず対象一覧を表示

【出力】
food-bio-atoms.json を上書き（バックアップを food-bio-atoms.json.bak に保存）
"""

import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Optional

ROOT     = Path(__file__).parent.parent
ATOMS_FILE = ROOT / "data" / "seed-atoms" / "food-bio-atoms.json"
BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# 検索対象とするカラム名（英語名で検索）
TARGET_TYPES = {"ingredient", "enzyme"}

# 単体化合物として検索できない Atom（混合物・高分子・生物・酵素など）
SKIP_KEYWORDS = {
    # 食品・混合物
    "Wheat protein", "Gluten", "Soy protein", "Cow's milk", "Whey protein",
    "Dietary fiber", "Green tea", "Germinated brown rice", "Oats",
    "Black vinegar (Kurozu)", "Grape seed proanthocyanidins (OPC)",
    "Collagen peptide", "Pectin", "Hyaluronic acid",
    "Chlorella", "Psyllium husk",
    # 酵素・タンパク質（高分子 → PubChem では正しく検索できない）
    "Protease", "Lactase (beta-galactosidase)", "Amylase", "Lipase",
    "Phytase", "Asparaginase", "Cellulase", "Transglutaminase (TGase)",
    "Nattokinase", "Casein",
}

# 代表的バイオアクティブ化合物で検索するオーバーライド (atom_id → PubChem検索名)
# エキス・ハーブなど「単一化合物ではないが代表化合物がある」Atom に使用
SEARCH_OVERRIDES: dict[str, str] = {
    "atom_fos":            "1-Kestose",                    # FOS の代表的三糖
    "atom_rhodiola":       "Salidroside",                  # ロジオラの主要バイオアクティブ
    "atom_panax_ginseng":  "Ginsenoside Rb1",              # 人参の主要ジンセノサイド
    "atom_cordyceps":      "Cordycepin",                   # コルジセプスの代表活性成分
    "atom_lions_mane":     "Erinacine A",                  # 山伏茸の代表バイオアクティブ
    "atom_grape_polyphenol": "Procyanidin B2",             # OPCの代表的二量体
    "atom_oat_fiber":      "beta-D-glucan",                # オーツの主要食物繊維
    "atom_green_tea":      "Epigallocatechin gallate",     # 緑茶の主要カテキン
}


def pubchem_search(name: str) -> Optional[dict]:
    """
    PubChem で化合物名を検索し、最初のヒットの情報を返す。
    見つからなければ None。
    """
    encoded = urllib.parse.quote(name)
    url = f"{BASE_URL}/compound/name/{encoded}/property/MolecularFormula,MolecularWeight,IsomericSMILES,InChIKey/JSON"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FormuleFuseStudio/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        props = data["PropertyTable"]["Properties"][0]
        cid = props["CID"]
        return {
            "pubchem_cid":       cid,
            "molecular_formula": props.get("MolecularFormula"),
            "molecular_weight":  props.get("MolecularWeight"),
            "smiles":            props.get("IsomericSMILES"),
            "inchikey":          props.get("InChIKey"),
            "pubchem_url":       f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
        }
    except urllib.error.HTTPError:
        return None   # 404 / 400（曖昧な名前）はスキップ
    except Exception:
        return None


def main():
    dry_run = "--dry-run" in sys.argv

    atoms = json.loads(ATOMS_FILE.read_text(encoding="utf-8"))
    # override対象 + 通常対象を結合
    override_targets = [
        a for a in atoms
        if a["atom_id"] in SEARCH_OVERRIDES and not a.get("compound")
    ]
    normal_targets = [
        a for a in atoms
        if a.get("atom_type") in TARGET_TYPES
        and a.get("name_en") not in SKIP_KEYWORDS
        and a["atom_id"] not in SEARCH_OVERRIDES
        and not a.get("compound")             # 既に付与済みはスキップ
    ]
    targets = override_targets + normal_targets

    print(f"🔬 PubChem エンリッチ対象: {len(targets)} Atom"
          f"（override {len(override_targets)} / 通常 {len(normal_targets)}）")
    if dry_run:
        for a in targets:
            override = SEARCH_OVERRIDES.get(a["atom_id"], "")
            suffix = f"  [override: {override}]" if override else ""
            print(f"  • {a['atom_id']}  {a['name_en']}{suffix}")
        return

    # バックアップ
    bak = ATOMS_FILE.with_suffix(".json.bak")
    bak.write_bytes(ATOMS_FILE.read_bytes())
    print(f"💾 バックアップ: {bak.name}")

    atom_index = {a["atom_id"]: a for a in atoms}
    hit = 0
    miss = 0

    for i, target in enumerate(targets, 1):
        aid = target["atom_id"]
        if aid in SEARCH_OVERRIDES:
            search_name = SEARCH_OVERRIDES[aid]
        else:
            name = target["name_en"]
            # 括弧内の補足・スラッシュ区切りを除去して検索
            search_name = name.split("(")[0].split("/")[0].strip()

        label = target["name_en"]
        print(f"[{i:>2}/{len(targets)}] {label} ({search_name}) ...", end=" ", flush=True)
        result = pubchem_search(search_name)

        if result:
            atom_index[target["atom_id"]]["compound"] = result
            print(f"✅  CID={result['pubchem_cid']}  {result.get('molecular_formula', '-')}")
            hit += 1
        else:
            print("—  not found")
            miss += 1

        # PubChem の利用規約に従いレートリミット（5 req/sec 以下）
        time.sleep(0.25)

    # 上書き保存
    ATOMS_FILE.write_text(
        json.dumps(list(atom_index.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ 完了  hit={hit}  miss={miss}")
    print(f"💾 保存: {ATOMS_FILE}")
    print("\n次のステップ:")
    print("  python3 scripts/generate_docs.py")


if __name__ == "__main__":
    main()
