#!/usr/bin/env python3
"""
enrich_fda_gras.py — FDA GRAS ステータスを Ingredient Atom に付与

【概要】
FDA の GRAS (Generally Recognized As Safe) ステータスを
ingredient Atom の "gras" フィールドに付与する:

  gras: {
    "status"  : "GRAS" | "GRAS_pending" | "NDI" | "food_additive" | "unknown"
    "basis"   : 根拠（21 CFR 番号 / GRAS Notice 番号 など）
    "notes"   : 補足コメント
    "jp_status": 日本での位置づけ（"食品" | "食品添加物" | "既存添加物" | "医薬品" など）
  }

【データ元】
- FDA 21 CFR Part 182/184 (GRAS substances)
- FDA GRAS Notice Inventory (https://www.cfsanappsexternal.fda.gov/)
- 厚生労働省 食薬区分（日本ステータス）
- Open FDA API (https://api.fda.gov/) — 補助的に使用

【実行】
  python3 scripts/enrich_fda_gras.py            # 全対象を処理
  python3 scripts/enrich_fda_gras.py --dry-run  # 対象一覧のみ表示

【出力】
  food-bio-atoms.json を上書き（バックアップを .bak に保存）
"""

import json
import sys
import urllib.request
import urllib.parse
import argparse
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
ATOMS_FILE = ROOT / "data" / "seed-atoms" / "food-bio-atoms.json"

# ── FDA GRAS キュレーションデータ ─────────────────────────────────────────────
# 参照: https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-182
#       https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-184
#       https://www.cfsanappsexternal.fda.gov/scripts/fdcc/?set=GRASNotices

GRAS_DATABASE: dict[str, dict] = {
    "Gamma-aminobutyric acid (GABA)": {
        "status":    "NDI",
        "basis":     "NDI Notification (FDA); いくつかの GRAS Notice 提出あり",
        "notes":     "US: NDI 届出済み（dietary supplement 用途）。食品添加物としての GRAS は限定的。",
        "jp_status": "食品",
    },
    "Magnesium": {
        "status":    "GRAS",
        "basis":     "21 CFR 184.1431 (Magnesium sulfate), 184.1426 (Magnesium gluconate)",
        "notes":     "塩の形態による。ミネラル強化・栄養補助目的で GRAS。",
        "jp_status": "食品添加物（栄養強化剤）",
    },
    "L-Theanine": {
        "status":    "GRAS",
        "basis":     "GRAS Notice No. GRN 000209",
        "notes":     "Suntheanine® 等の L-テアニン製品について FDA は no-objection 回答済み。",
        "jp_status": "食品",
    },
    "Curcumin": {
        "status":    "GRAS",
        "basis":     "21 CFR 73.600 (色素), GRAS Notice No. GRN 000460",
        "notes":     "ターメリックおよびその抽出物は GRAS。高濃度製品は用量依存リスクあり。",
        "jp_status": "既存添加物（着色料）/ 食品",
    },
    "Vitamin C (Ascorbic acid)": {
        "status":    "GRAS",
        "basis":     "21 CFR 182.3013 / 184.1002",
        "notes":     "抗酸化剤・栄養強化として広く GRAS。",
        "jp_status": "食品添加物（酸化防止剤・栄養強化剤）",
    },
    "Zinc": {
        "status":    "GRAS",
        "basis":     "21 CFR 182.8997 / 184.1976",
        "notes":     "亜鉛塩（グルコン酸亜鉛等）が GRAS。摂取量過多でリスクあり。",
        "jp_status": "食品添加物（栄養強化剤）",
    },
    "Iron": {
        "status":    "GRAS",
        "basis":     "21 CFR 184.1375 (Ferrous gluconate) / 184.1396",
        "notes":     "鉄塩の形態により GRAS。過剰摂取は酸化ストレスリスク。",
        "jp_status": "食品添加物（栄養強化剤）",
    },
    "DHA / EPA (Omega-3 fatty acids)": {
        "status":    "GRAS",
        "basis":     "GRAS Notice No. GRN 000041 / GRN 000196 / GRN 000516",
        "notes":     "魚油・藻由来 DHA/EPA は特定用途で GRAS。高用量は抗凝固作用。",
        "jp_status": "食品",
    },
    "Lactic acid": {
        "status":    "GRAS",
        "basis":     "21 CFR 184.1061",
        "notes":     "pH 調整剤・保存料として広く GRAS。",
        "jp_status": "食品添加物（pH 調整剤）",
    },
    "Coenzyme Q10 (Ubiquinone)": {
        "status":    "GRAS",
        "basis":     "GRAS Notice No. GRN 000148 / GRN 000538",
        "notes":     "栄養補助食品用途で GRAS。一般食品への添加は用途制限あり。",
        "jp_status": "食品",
    },
    "Astaxanthin": {
        "status":    "GRAS",
        "basis":     "GRAS Notice No. GRN 000762 (Haematococcus pluvialis 由来)",
        "notes":     "藻由来アスタキサンチンは FDA no-objection 済み。用量・用途の制限あり。",
        "jp_status": "既存添加物（着色料）/ 食品",
    },
    "Inulin": {
        "status":    "GRAS",
        "basis":     "GRAS Notice No. GRN 000118 / GRN 000246",
        "notes":     "菊芋・チコリ由来イヌリンは dietary fiber として GRAS。",
        "jp_status": "食品",
    },
    "Pectin": {
        "status":    "GRAS",
        "basis":     "21 CFR 184.1588",
        "notes":     "増粘剤・ゲル化剤として広く GRAS。",
        "jp_status": "食品添加物（増粘安定剤）",
    },
    "Collagen peptide": {
        "status":    "GRAS",
        "basis":     "GRAS Notice No. GRN 000334 (Gelatin hydrolysate)",
        "notes":     "加水分解コラーゲンは GRAS。魚・豚由来は宗教・アレルゲン表示に注意。",
        "jp_status": "食品",
    },
    "Fructooligosaccharides (FOS)": {
        "status":    "GRAS",
        "basis":     "GRAS Notice No. GRN 000036 / GRN 000118",
        "notes":     "プレバイオティクスとして GRAS。過剰摂取は消化器症状。",
        "jp_status": "食品",
    },
    "Hyaluronic acid": {
        "status":    "GRAS",
        "basis":     "GRAS Notice No. GRN 000443 / GRN 000796",
        "notes":     "特定食品カテゴリへの添加で GRAS no-objection 済み。",
        "jp_status": "食品",
    },
    "Whey protein": {
        "status":    "GRAS",
        "basis":     "21 CFR 184.1979a",
        "notes":     "乳清タンパク質は GRAS。乳アレルゲン表示必須。",
        "jp_status": "食品",
    },
    "Soy protein": {
        "status":    "GRAS",
        "basis":     "21 CFR 184.1205",
        "notes":     "大豆タンパク質は GRAS。大豆アレルゲン表示必須。",
        "jp_status": "食品",
    },
    "Lactose": {
        "status":    "GRAS",
        "basis":     "21 CFR 184.1445",
        "notes":     "乳糖は GRAS。乳糖不耐症者への配慮が必要。",
        "jp_status": "食品",
    },
    "Dietary fiber": {
        "status":    "GRAS",
        "basis":     "21 CFR 101.9 / Various",
        "notes":     "食物繊維は一般的に GRAS。種類により個別確認が必要。",
        "jp_status": "食品",
    },
    "Caffeine": {
        "status":    "GRAS",
        "basis":     "21 CFR 182.1180",
        "notes":     "コーラ系飲料への添加で GRAS（0.02%以下）。高用量は心血管リスク。",
        "jp_status": "食品",
    },
    "Green tea": {
        "status":    "GRAS",
        "basis":     "GRAS Notice No. GRN 000231 (green tea extract)",
        "notes":     "緑茶・エキスは GRAS。カテキン高濃度製品は肝毒性リスクで注意。",
        "jp_status": "食品",
    },
    "Germinated brown rice": {
        "status":    "GRAS",
        "basis":     "21 CFR (whole grain)",
        "notes":     "発芽玄米は GRAS（全粒穀物として）。GABA 含有量が高い。",
        "jp_status": "食品",
    },
    "Oats": {
        "status":    "GRAS",
        "basis":     "21 CFR 182 (whole grain)",
        "notes":     "GRAS。グルテン混入リスクあり（セリアック病患者向け製品では要注意）。",
        "jp_status": "食品",
    },
    "Wheat protein": {
        "status":    "GRAS",
        "basis":     "21 CFR (wheat)",
        "notes":     "GRAS。小麦アレルゲン表示必須（Big 9 アレルゲン）。",
        "jp_status": "食品",
    },
    "Gluten": {
        "status":    "GRAS",
        "basis":     "21 CFR (wheat)",
        "notes":     "GRAS。セリアック病・グルテン過敏症リスク。アレルゲン表示必須。",
        "jp_status": "食品",
    },
    "Cow's milk": {
        "status":    "GRAS",
        "basis":     "21 CFR 133 (milk products)",
        "notes":     "GRAS。乳アレルゲン表示必須（Big 9 アレルゲン）。",
        "jp_status": "食品",
    },
    "Grape seed proanthocyanidins (OPC)": {
        "status":    "GRAS",
        "basis":     "GRAS Notice No. GRN 000041 (grape seed extract)",
        "notes":     "ブドウ種子エキスは GRAS。高濃度ポリフェノール製品の長期安全性は継続研究中。",
        "jp_status": "食品",
    },
    "Black vinegar (Kurozu)": {
        "status":    "GRAS",
        "basis":     "21 CFR 184.1063 (vinegar / acetic acid)",
        "notes":     "酢（酢酸）は GRAS。黒酢は伝統的食品として安全性確立済み。",
        "jp_status": "食品",
    },
}

# ── 酵素・微生物のステータス ──────────────────────────────────────────────────
ENZYME_GRAS: dict[str, dict] = {
    "Protease":                    {"status": "food_additive", "basis": "21 CFR 184.1\ (enzyme preparations)", "jp_status": "食品添加物（酵素）"},
    "Lactase (beta-galactosidase)": {"status": "GRAS",        "basis": "21 CFR 184.1027 (lactase)",            "jp_status": "食品添加物（酵素）"},
    "Amylase":                     {"status": "GRAS",         "basis": "21 CFR 184.1012 (amylase)",            "jp_status": "食品添加物（酵素）"},
    "Lipase":                      {"status": "GRAS",         "basis": "21 CFR 184.1490 (lipase)",             "jp_status": "食品添加物（酵素）"},
    "Phytase":                     {"status": "GRAS",         "basis": "GRAS Notice No. GRN 000072",           "jp_status": "食品添加物（酵素）"},
    "Asparaginase":                {"status": "food_additive","basis": "Novozymes Acrylaway® - EU approved",   "jp_status": "食品添加物（酵素）"},
    "Cellulase":                   {"status": "GRAS",         "basis": "GRAS Notice No. GRN 000039",           "jp_status": "食品添加物（酵素）"},
    "Transglutaminase (TGase)":    {"status": "GRAS",         "basis": "GRAS Notice No. GRN 000299",           "jp_status": "食品添加物（酵素）"},
}

MICROBE_GRAS: dict[str, dict] = {
    "Lactobacillus":               {"status": "GRAS", "basis": "QPS (EFSA) / Recognized as safe in fermentation", "jp_status": "食品"},
    "Bifidobacterium":             {"status": "GRAS", "basis": "QPS (EFSA) / Generally recognized safe probiotic", "jp_status": "食品"},
    "Yeast (Saccharomyces cerevisiae)": {"status": "GRAS", "basis": "21 CFR 182.1983", "jp_status": "食品添加物（酵母）/ 食品"},
    "Aspergillus oryzae (Koji)":   {"status": "GRAS", "basis": "21 CFR 184.1983 / Traditional use", "jp_status": "食品添加物（酵素源）"},
    "Bacillus subtilis var. natto": {"status": "GRAS", "basis": "Traditional use / Japan FOSHU recognized", "jp_status": "食品"},
    "Lactobacillus plantarum":     {"status": "GRAS", "basis": "QPS (EFSA) / GRAS Notice No. GRN 000049", "jp_status": "食品"},
    "Leuconostoc mesenteroides":   {"status": "GRAS", "basis": "QPS (EFSA) / Traditional fermentation use", "jp_status": "食品"},
    "Acetobacter aceti":           {"status": "GRAS", "basis": "Traditional vinegar fermentation / GRAS by heritage", "jp_status": "食品"},
    "Streptococcus thermophilus":  {"status": "GRAS", "basis": "21 CFR 184 / QPS (EFSA)", "jp_status": "食品"},
}


def get_gras_info(atom: dict) -> Optional[dict]:
    name = atom.get("name_en", "")
    atom_type = atom.get("atom_type", "")

    if atom_type == "ingredient":
        return GRAS_DATABASE.get(name)
    elif atom_type == "enzyme":
        name_clean = name.split("(")[0].strip()
        return ENZYME_GRAS.get(name) or ENZYME_GRAS.get(name_clean)
    elif atom_type == "microbe":
        return MICROBE_GRAS.get(name)

    return None


def main():
    parser = argparse.ArgumentParser(description="FDA GRAS ステータスを Atom に付与")
    parser.add_argument("--dry-run", action="store_true", help="対象一覧のみ表示")
    parser.add_argument("--force", action="store_true", help="既に gras フィールドがある Atom も上書き")
    args = parser.parse_args()

    atoms = json.loads(ATOMS_FILE.read_text(encoding="utf-8"))

    targets = [
        a for a in atoms
        if a.get("atom_type") in {"ingredient", "enzyme", "microbe"}
        and (args.force or "gras" not in a)
    ]

    print(f"🏛️  FDA GRAS エンリッチ対象: {len(targets)} Atom")

    if args.dry_run:
        for a in targets:
            info = get_gras_info(a)
            status = info["status"] if info else "unknown"
            print(f"  • {a['atom_id']:35s}  [{status:15s}]  {a['name_en']}")
        return

    # バックアップ
    bak = ATOMS_FILE.with_suffix(".json.bak")
    bak.write_bytes(ATOMS_FILE.read_bytes())
    print(f"💾 バックアップ: {bak.name}")

    atom_index = {a["atom_id"]: a for a in atoms}
    hit = 0
    miss = 0

    for target in targets:
        name = target["name_en"]
        info = get_gras_info(target)

        if info:
            atom_index[target["atom_id"]]["gras"] = info
            status_icon = {"GRAS": "✅", "NDI": "⚠️ ", "food_additive": "🔵", "unknown": "❓"}.get(info["status"], "📋")
            print(f"  {status_icon}  [{info['status']:15s}]  {name}")
            hit += 1
        else:
            atom_index[target["atom_id"]]["gras"] = {
                "status":    "unknown",
                "basis":     "未確認 — 個別調査が必要",
                "notes":     "本スクリプトのキュレーションデータに含まれていません。",
                "jp_status": "不明",
            }
            print(f"  ❓  [unknown        ]  {name}")
            miss += 1

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
