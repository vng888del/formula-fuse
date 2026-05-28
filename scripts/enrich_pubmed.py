#!/usr/bin/env python3
"""
enrich_pubmed.py — NCBI PubMed eUtils で Atom にエビデンス論文を付与

【概要】
NCBI Entrez eUtils (https://eutils.ncbi.nlm.nih.gov/) を使って
全 Atom に関連論文トップ5を付与する（atom 内 "pubmed_evidence" キー）:

  pubmed_evidence: [
    {
      "pmid"    : 論文 PMID
      "title"   : タイトル
      "authors" : 著者リスト (最大3名)
      "journal" : ジャーナル名
      "year"    : 発表年
      "pubmed_url": PubMed URL
    },
    ...
  ]

【API】
  NCBI Entrez eUtils — 完全無料・APIキー不要
  APIキー登録で 10 req/sec まで (未登録は 3 req/sec)
  https://www.ncbi.nlm.nih.gov/account/ で無料取得

【実行】
  python3 scripts/enrich_pubmed.py                       # 全 Atom
  python3 scripts/enrich_pubmed.py --api-key YOUR_KEY    # 高速モード（10 req/sec）
  python3 scripts/enrich_pubmed.py --dry-run             # 対象一覧のみ
  python3 scripts/enrich_pubmed.py --atom-id atom_gaba   # 1件テスト

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
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# 全 atom_type を対象
TARGET_TYPES = {"ingredient", "enzyme", "microbe", "condition", "goal"}

# 検索クエリのカスタマイズ（atom_id → 検索語）
QUERY_OVERRIDES = {
    "atom_gaba":        "GABA gamma-aminobutyric acid food supplement",
    "atom_lactase":     "lactase beta-galactosidase lactose intolerance",
    "atom_magnesium":   "magnesium supplement health benefits",
    "atom_vitamin_c":   "vitamin C ascorbic acid health",
    "atom_theanine":    "L-theanine green tea relaxation",
    "atom_curcumin":    "curcumin turmeric anti-inflammatory",
    "atom_dha_epa":     "DHA EPA omega-3 fatty acids health",
    "atom_coq10":       "coenzyme Q10 ubiquinone antioxidant",
    "atom_astaxanthin": "astaxanthin antioxidant health",
    "atom_zinc":        "zinc mineral supplement immunity",
    "atom_iron":        "iron mineral supplement health",
    "atom_lactic_acid": "lactic acid fermentation food",
    "atom_lactobacillus": "Lactobacillus probiotic health",
    "atom_bifidobacterium": "Bifidobacterium probiotic gut health",
    "atom_yeast":       "Saccharomyces cerevisiae fermentation",
    "atom_koji":        "Aspergillus oryzae koji fermentation",
    "atom_natto_bacillus": "Bacillus subtilis natto nattokinase",
    "atom_protease":    "protease enzyme food supplement",
    "atom_amylase":     "amylase starch digestion enzyme",
    "atom_phytase":     "phytase phytic acid mineral absorption",
    "atom_asparaginase": "asparaginase acrylamide food safety",
    "atom_transglutaminase": "transglutaminase food texture protein crosslinking",
}


def build_query(atom: dict) -> str:
    """Atom から PubMed 検索クエリを構築する。"""
    atom_id = atom["atom_id"]
    if atom_id in QUERY_OVERRIDES:
        return QUERY_OVERRIDES[atom_id]

    name = atom["name_en"].split("(")[0].split("/")[0].strip()
    atom_type = atom["atom_type"]

    # atom_type 別にサフィックス追加
    suffix_map = {
        "ingredient": "food supplement health",
        "enzyme":     "enzyme activity food",
        "microbe":    "probiotic fermentation health",
        "condition":  "food processing health",
        "goal":       "functional food health",
    }
    suffix = suffix_map.get(atom_type, "food health")
    return f"{name} {suffix}"


def esearch(query: str, api_key: Optional[str], max_ids: int = 5) -> list:
    """PubMed で検索し PMID リストを返す。"""
    params = {
        "db":      "pubmed",
        "term":    query,
        "retmax":  max_ids,
        "retmode": "json",
        "sort":    "relevance",
    }
    if api_key:
        params["api_key"] = api_key

    url = f"{BASE_URL}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FormuleFuseStudio/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []


def efetch_summaries(pmids: list, api_key: Optional[str]) -> list:
    """PMID リストから論文サマリーを取得する。"""
    if not pmids:
        return []

    params = {
        "db":      "pubmed",
        "id":      ",".join(pmids),
        "retmode": "json",
        "rettype": "docsum",
    }
    if api_key:
        params["api_key"] = api_key

    url = f"{BASE_URL}/esummary.fcgi?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FormuleFuseStudio/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        results = []
        for pmid in pmids:
            doc = data.get("result", {}).get(pmid)
            if not doc or doc.get("error"):
                continue

            # 著者リスト（最大3名）
            authors = []
            for auth in doc.get("authors", [])[:3]:
                name = auth.get("name", "")
                if name:
                    authors.append(name)

            # 発表年
            pub_date = doc.get("pubdate", "")
            year = pub_date[:4] if pub_date else ""

            results.append({
                "pmid":       pmid,
                "title":      doc.get("title", "")[:200],
                "authors":    authors,
                "journal":    doc.get("source", ""),
                "year":       year,
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })

        return results

    except Exception:
        return []


def enrich_atom(atom: dict, api_key: Optional[str]) -> Optional[list]:
    """1つの Atom に PubMed 論文リストを付与する。"""
    query = build_query(atom)
    pmids = esearch(query, api_key, max_ids=5)
    if not pmids:
        return None
    return efetch_summaries(pmids, api_key)


def main():
    parser = argparse.ArgumentParser(description="PubMed エビデンスを Atom に付与")
    parser.add_argument("--api-key", default=None, help="NCBI API キー（省略可、10 req/sec に）")
    parser.add_argument("--dry-run", action="store_true", help="対象一覧のみ表示")
    parser.add_argument("--atom-id", help="特定の atom_id のみ処理")
    parser.add_argument("--force", action="store_true", help="既に pubmed_evidence がある Atom も再取得")
    args = parser.parse_args()

    atoms = json.loads(ATOMS_FILE.read_text(encoding="utf-8"))

    targets = [
        a for a in atoms
        if a.get("atom_type") in TARGET_TYPES
        and (args.force or "pubmed_evidence" not in a)
    ]

    if args.atom_id:
        targets = [a for a in targets if a.get("atom_id") == args.atom_id]

    print(f"📚 PubMed エンリッチ対象: {len(targets)} Atom")
    if args.api_key:
        print("   🔑 API キーあり（10 req/sec モード）")
    else:
        print("   ⚠️  API キーなし（3 req/sec モード — 取得は https://www.ncbi.nlm.nih.gov/account/）")

    if args.dry_run:
        for a in targets:
            q = build_query(a)
            print(f"  • {a['atom_id']:30s}  query: {q}")
        return

    # バックアップ
    bak = ATOMS_FILE.with_suffix(".json.bak")
    bak.write_bytes(ATOMS_FILE.read_bytes())
    print(f"💾 バックアップ: {bak.name}")

    atom_index = {a["atom_id"]: a for a in atoms}
    hit = 0
    miss = 0

    # API キーなし: 3 req/sec → 0.4s 待機
    # API キーあり: 10 req/sec → 0.12s 待機
    wait = 0.12 if args.api_key else 0.4

    for i, target in enumerate(targets, 1):
        name = target["name_en"]
        print(f"[{i:>2}/{len(targets)}] {name[:40]} ...", end=" ", flush=True)

        # esearch + efetch = 2 API 呼び出し
        papers = enrich_atom(target, args.api_key)

        if papers:
            atom_index[target["atom_id"]]["pubmed_evidence"] = papers
            print(f"✅  {len(papers)} papers  (top: {papers[0]['year']} {papers[0]['journal'][:25]})")
            hit += 1
        else:
            print("—  not found")
            miss += 1

        time.sleep(wait * 2)  # esearch + efetch の合計分

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
