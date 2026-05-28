#!/usr/bin/env python3
"""
enrich_uniprot.py — UniProt REST API で enzyme / microbe Atom に機能データを付与

【概要】
UniProt (https://www.uniprot.org/) の REST API を使って
enzyme・microbe Atom に以下を付与する（atom 内 "uniprot" キー）:

  enzyme Atom:
    - uniprot_id       : UniProt エントリ ID (例: P00698)
    - protein_name     : 推奨タンパク質名
    - gene_names       : 遺伝子名リスト
    - organism         : 生物種
    - ec_numbers       : EC 番号リスト (例: ["3.2.1.17"])
    - function_comment : 機能コメント
    - subcellular_location: 細胞内局在
    - catalytic_activity  : 触媒反応リスト
    - uniprot_url      : UniProt ページ URL

  microbe Atom:
    - taxonomy_id  : NCBI Taxonomy ID
    - organism     : 正式学名
    - lineage      : 分類階層 (Kingdom → Species)
    - uniprot_url  : UniProt Taxonomy ページ URL

【実行】
  python3 scripts/enrich_uniprot.py              # 全対象を処理
  python3 scripts/enrich_uniprot.py --dry-run    # 対象一覧のみ表示
  python3 scripts/enrich_uniprot.py --atom-id atom_lactase

【出力】
  food-bio-atoms.json を上書き（バックアップを .bak に保存）
"""

import json
import sys
import time
import argparse
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
ATOMS_FILE = ROOT / "data" / "seed-atoms" / "food-bio-atoms.json"
BASE_URL = "https://rest.uniprot.org"

TARGET_TYPES = {"enzyme", "microbe"}

# UniProt 検索クエリの手動マッピング（デフォルト検索が曖昧な場合）
QUERY_OVERRIDES = {
    # 酵素: 「Swiss-Prot + EC番号で絞る」
    "atom_protease":          "serine protease reviewed:true organism_id:9606",
    "atom_lactase":           "beta-galactosidase reviewed:true ec:3.2.1.23",
    "atom_amylase":           "alpha-amylase reviewed:true ec:3.2.1.1",
    "atom_lipase":            "triacylglycerol lipase reviewed:true ec:3.1.1.3",
    "atom_phytase":           "phytase reviewed:true ec:3.1.3.8",
    "atom_asparaginase":      "asparaginase reviewed:true ec:3.5.1.1",
    "atom_cellulase":         "cellulase reviewed:true ec:3.2.1.4",
    "atom_transglutaminase":  "transglutaminase reviewed:true ec:2.3.2.13",
    # 微生物: NCBI Taxonomy 検索
    "atom_lactobacillus":          "taxonomy_id:1578",
    "atom_bifidobacterium":        "taxonomy_id:1678",
    "atom_yeast":                  "taxonomy_id:4932",
    "atom_koji":                   "taxonomy_id:5062",
    "atom_natto_bacillus":         "taxonomy_id:1423",
    "atom_lactobacillus_plantarum": "taxonomy_id:1590",
    "atom_leuconostoc":            "taxonomy_id:1243",
    "atom_acetobacter":            "taxonomy_id:435",
    "atom_streptococcus_thermophilus": "taxonomy_id:1308",
}

# 微生物の Taxonomy ID → 正式学名・系統
MICROBE_TAXONOMY = {
    "atom_lactobacillus":          {"taxonomy_id": 1578,  "organism": "Lactobacillus",               "lineage": ["Bacteria", "Firmicutes", "Bacilli", "Lactobacillales", "Lactobacillaceae", "Lactobacillus"]},
    "atom_bifidobacterium":        {"taxonomy_id": 1678,  "organism": "Bifidobacterium",             "lineage": ["Bacteria", "Actinobacteria", "Bifidobacteriales", "Bifidobacteriaceae", "Bifidobacterium"]},
    "atom_yeast":                  {"taxonomy_id": 4932,  "organism": "Saccharomyces cerevisiae",    "lineage": ["Eukaryota", "Fungi", "Ascomycota", "Saccharomycetes", "Saccharomycetales", "Saccharomycetaceae", "Saccharomyces"]},
    "atom_koji":                   {"taxonomy_id": 5062,  "organism": "Aspergillus oryzae",          "lineage": ["Eukaryota", "Fungi", "Ascomycota", "Eurotiomycetes", "Eurotiales", "Aspergillaceae", "Aspergillus"]},
    "atom_natto_bacillus":         {"taxonomy_id": 1423,  "organism": "Bacillus subtilis",           "lineage": ["Bacteria", "Firmicutes", "Bacilli", "Bacillales", "Bacillaceae", "Bacillus"]},
    "atom_lactobacillus_plantarum": {"taxonomy_id": 1590, "organism": "Lactiplantibacillus plantarum","lineage": ["Bacteria", "Firmicutes", "Bacilli", "Lactobacillales", "Lactobacillaceae", "Lactiplantibacillus"]},
    "atom_leuconostoc":            {"taxonomy_id": 1243,  "organism": "Leuconostoc mesenteroides",   "lineage": ["Bacteria", "Firmicutes", "Bacilli", "Lactobacillales", "Leuconostocaceae", "Leuconostoc"]},
    "atom_acetobacter":            {"taxonomy_id": 435,   "organism": "Acetobacter aceti",           "lineage": ["Bacteria", "Proteobacteria", "Alphaproteobacteria", "Rhodospirillales", "Acetobacteraceae", "Acetobacter"]},
    "atom_streptococcus_thermophilus": {"taxonomy_id": 1308, "organism": "Streptococcus thermophilus", "lineage": ["Bacteria", "Firmicutes", "Bacilli", "Lactobacillales", "Streptococcaceae", "Streptococcus"]},
}


def search_enzyme(atom_id: str, name_en: str) -> Optional[dict]:
    """UniProt で酵素を検索し、トップヒットの詳細を返す。"""
    query = QUERY_OVERRIDES.get(atom_id, f"{name_en.split('(')[0].strip()} reviewed:true")
    params = urllib.parse.urlencode({
        "query":  query,
        "fields": "accession,protein_name,gene_names,organism_name,ec,ft_act_site,cc_function,cc_subcellular_location,cc_catalytic_activity",
        "format": "json",
        "size":   1,
    })
    url = f"{BASE_URL}/uniprotkb/search?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FormuleFuseStudio/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        results = data.get("results", [])
        if not results:
            return None

        entry = results[0]
        acc = entry.get("primaryAccession", "")

        # タンパク質名
        pn = entry.get("proteinDescription", {})
        recommended = pn.get("recommendedName", {})
        protein_name = (
            recommended.get("fullName", {}).get("value")
            or pn.get("submissionNames", [{}])[0].get("fullName", {}).get("value", "")
        )

        # 遺伝子名
        genes = [g.get("geneName", {}).get("value", "") for g in entry.get("genes", [])]
        genes = [g for g in genes if g]

        # EC 番号
        ec_numbers = [
            n.get("value", "")
            for n in recommended.get("ecNumbers", [])
        ]

        # 生物種
        organism = entry.get("organism", {}).get("scientificName", "")

        # 機能コメント
        func_comment = ""
        for comment in entry.get("comments", []):
            if comment.get("commentType") == "FUNCTION":
                texts = comment.get("texts", [])
                if texts:
                    func_comment = texts[0].get("value", "")[:300]
                    break

        # 触媒反応
        catalytic = []
        for comment in entry.get("comments", []):
            if comment.get("commentType") == "CATALYTIC ACTIVITY":
                rxn = comment.get("reaction", {})
                name = rxn.get("name", "")
                if name:
                    catalytic.append(name[:200])

        # 細胞内局在
        subcellular = []
        for comment in entry.get("comments", []):
            if comment.get("commentType") == "SUBCELLULAR LOCATION":
                for loc in comment.get("subcellularLocations", []):
                    loc_val = loc.get("location", {}).get("value", "")
                    if loc_val:
                        subcellular.append(loc_val)

        return {
            "uniprot_id":           acc,
            "protein_name":         protein_name,
            "gene_names":           genes[:5],
            "organism":             organism,
            "ec_numbers":           ec_numbers,
            "function_comment":     func_comment,
            "subcellular_location": subcellular[:3],
            "catalytic_activity":   catalytic[:2],
            "uniprot_url":          f"https://www.uniprot.org/uniprotkb/{acc}",
        }

    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("⚠️  Rate limit, waiting 30s...", flush=True)
            time.sleep(30)
        return None
    except Exception:
        return None


def enrich_microbe(atom_id: str) -> Optional[dict]:
    """微生物は固定 Taxonomy データを返す（API 呼び出し不要）。"""
    info = MICROBE_TAXONOMY.get(atom_id)
    if not info:
        return None
    tid = info["taxonomy_id"]
    return {
        "taxonomy_id": tid,
        "organism":    info["organism"],
        "lineage":     info["lineage"],
        "uniprot_url": f"https://www.uniprot.org/taxonomy/{tid}",
    }


def main():
    parser = argparse.ArgumentParser(description="UniProt データを enzyme/microbe Atom に付与")
    parser.add_argument("--dry-run", action="store_true", help="対象一覧のみ表示")
    parser.add_argument("--atom-id", help="特定の atom_id のみ処理")
    parser.add_argument("--force", action="store_true", help="既に uniprot フィールドがある Atom も再取得")
    args = parser.parse_args()

    atoms = json.loads(ATOMS_FILE.read_text(encoding="utf-8"))

    targets = [
        a for a in atoms
        if a.get("atom_type") in TARGET_TYPES
        and (args.force or "uniprot" not in a)
    ]

    if args.atom_id:
        targets = [a for a in targets if a.get("atom_id") == args.atom_id]

    print(f"🔬 UniProt エンリッチ対象: {len(targets)} Atom")

    if args.dry_run:
        for a in targets:
            print(f"  • {a['atom_id']}  ({a['atom_type']})  {a['name_en']}")
        return

    # バックアップ
    bak = ATOMS_FILE.with_suffix(".json.bak")
    bak.write_bytes(ATOMS_FILE.read_bytes())
    print(f"💾 バックアップ: {bak.name}")

    atom_index = {a["atom_id"]: a for a in atoms}
    hit = 0
    miss = 0

    for i, target in enumerate(targets, 1):
        atom_id = target["atom_id"]
        atom_type = target["atom_type"]
        name = target["name_en"]

        print(f"[{i:>2}/{len(targets)}] ({atom_type}) {name} ...", end=" ", flush=True)

        if atom_type == "microbe":
            result = enrich_microbe(atom_id)
            if result:
                atom_index[atom_id]["uniprot"] = result
                print(f"✅  TaxID={result['taxonomy_id']}  {result['organism']}")
                hit += 1
            else:
                print("—  not found")
                miss += 1
            # 微生物は API 不要なので待機なし
            continue

        # 酵素: API 呼び出し
        result = search_enzyme(atom_id, name)
        if result:
            atom_index[atom_id]["uniprot"] = result
            ec = ", ".join(result["ec_numbers"]) or "-"
            print(f"✅  {result['uniprot_id']}  EC:{ec}  {result['protein_name'][:40]}")
            hit += 1
        else:
            print("—  not found")
            miss += 1

        time.sleep(0.5)

    # 上書き保存
    ATOMS_FILE.write_text(
        json.dumps(list(atom_index.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ 完了  hit={hit}  miss={miss}")
    print(f"💾 保存: {ATOMS_FILE}")
    print("\n次のステップ:")
    print("  python3 scripts/enrich_pubmed.py")


if __name__ == "__main__":
    main()
