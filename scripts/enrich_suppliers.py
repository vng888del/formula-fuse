#!/usr/bin/env python3
"""
enrich_suppliers.py — サプライヤー・OEM・品質情報を Atom に付与

【概要】
ingredient / enzyme / microbe Atom に以下を付与する（atom 内 "supplier_info" キー）:

  supplier_info: {
    "major_suppliers"   : 主要グローバルサプライヤー（ブランド名含む）
    "japan_suppliers"   : 日本市場主要サプライヤー
    "oem_forms"         : OEM 対応剤形（powder, capsule, tablet, drink 等）
    "typical_grade"     : 品質グレード（Food / Pharmaceutical / USP 等）
    "certifications"    : 取得が多い認証（USP, JP, Halal, Kosher, Non-GMO 等）
    "price_tier"        : 価格帯の目安（low / medium / high / very_high）
    "lead_time_weeks"   : 一般的なリードタイム（週数、目安）
    "min_order_qty"     : 最小発注量の目安（例: "1 kg", "25 kg"）
    "notes"             : 調達上の注意点
  }

【実行】
  python3 scripts/enrich_suppliers.py
  python3 scripts/enrich_suppliers.py --dry-run

【注意】
このスクリプトはキュレーション済みデータを使用します（API 不要）。
情報は 2024–2025 年時点のものであり、実際の調達時は各社に要確認。
"""

import json
import argparse
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
ATOMS_FILE = ROOT / "data" / "seed-atoms" / "food-bio-atoms.json"

# ── サプライヤーキュレーションデータ ──────────────────────────────────────────
# 参照: 各社 Web サイト、業界カタログ、展示会情報 (2024-2025)

SUPPLIER_DATABASE: dict[str, dict] = {

    # ── Ingredients ──────────────────────────────────────────────────────────

    "Gamma-aminobutyric acid (GABA)": {
        "major_suppliers": ["Pharma Foods International (PFI)", "Now Foods", "Source Naturals", "KAL"],
        "japan_suppliers": ["協和発酵バイオ", "Pharma Foods International (パーマフーズ)", "白鳥製薬"],
        "oem_forms": ["powder", "capsule", "tablet", "drink_mix"],
        "typical_grade": "Food / Pharmaceutical",
        "certifications": ["JHFA", "JP", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "発酵由来 GABA が品質面で優位。合成品との区別に注意。",
    },

    "Magnesium": {
        "major_suppliers": ["DSM", "BASF", "ICL (Israel Chemicals)", "Albion Minerals", "Balchem"],
        "japan_suppliers": ["太陽化学", "林純薬工業", "富田製薬"],
        "oem_forms": ["powder", "capsule", "tablet", "gummy"],
        "typical_grade": "Food / USP",
        "certifications": ["USP", "JP", "Halal", "Kosher", "Non-GMO"],
        "price_tier": "low",
        "lead_time_weeks": 2,
        "min_order_qty": "25 kg",
        "notes": "形態（酸化Mg/グリシン酸Mg/クエン酸Mg）で吸収率が大きく異なる。",
    },

    "L-Theanine": {
        "major_suppliers": ["Taiyo Kagaku (Suntheanine®)", "Kyowa Hakko Bio (Suntheanine® license)", "NOW Foods"],
        "japan_suppliers": ["太陽化学 (Suntheanine®)", "協和発酵バイオ"],
        "oem_forms": ["powder", "capsule", "tablet", "drink_mix", "tea_blend"],
        "typical_grade": "Food / Pharmaceutical",
        "certifications": ["GRAS (GRN 209)", "Non-GMO", "Kosher", "Halal"],
        "price_tier": "high",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "Suntheanine® はブランド保護あり。ジェネリック品は品質検証が必須。",
    },

    "Curcumin": {
        "major_suppliers": ["Sabinsa (BCM-95®, C3 Complex®)", "Natural Remedies (CurQfen®)", "DSM", "Arjuna Natural"],
        "japan_suppliers": ["太陽化学", "長谷川香料", "三菱商事ライフサイエンス"],
        "oem_forms": ["powder", "capsule", "softgel", "tablet", "drink"],
        "typical_grade": "Food / Standardized Extract",
        "certifications": ["GRAS", "Non-GMO", "Halal", "Kosher", "Organic (一部)"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "生物利用性が低いため、ペパリン添加や脂質封入型が主流。95%標準化品が多い。",
    },

    "Vitamin C (Ascorbic acid)": {
        "major_suppliers": ["DSM (QUALI-C®)", "BASF", "Xinfa Pharmaceutical (中国)", "Northeast Pharmaceutical"],
        "japan_suppliers": ["武田薬品工業 (QUALI-C®)", "三菱商事フードテック"],
        "oem_forms": ["powder", "tablet", "capsule", "drink", "effervescent"],
        "typical_grade": "Food / USP / EP",
        "certifications": ["USP", "JP", "EP", "Non-GMO", "Kosher", "Halal"],
        "price_tier": "low",
        "lead_time_weeks": 2,
        "min_order_qty": "25 kg",
        "notes": "中国産が市場を席巻。品質はサプライヤーにより差大。QUALI-C® はスコットランド産で高信頼。",
    },

    "Zinc": {
        "major_suppliers": ["Zinpro (Availa®-Zn)", "DSM", "Albion Minerals (OptiZinc®)", "Balchem"],
        "japan_suppliers": ["太陽化学", "林純薬工業"],
        "oem_forms": ["powder", "capsule", "tablet", "gummy"],
        "typical_grade": "Food / USP",
        "certifications": ["USP", "JP", "Halal", "Kosher"],
        "price_tier": "low",
        "lead_time_weeks": 2,
        "min_order_qty": "25 kg",
        "notes": "グルコン酸亜鉛・ピコリン酸亜鉛・ビスグリシン酸亜鉛の吸収率差に注意。",
    },

    "Iron": {
        "major_suppliers": ["DSM", "Aidea (Suferro®)", "Albion Minerals", "Balchem"],
        "japan_suppliers": ["太陽化学", "林純薬工業", "三菱商事フードテック"],
        "oem_forms": ["powder", "capsule", "tablet"],
        "typical_grade": "Food / USP",
        "certifications": ["USP", "JP", "Halal", "Kosher"],
        "price_tier": "low",
        "lead_time_weeks": 2,
        "min_order_qty": "25 kg",
        "notes": "非ヘム鉄は吸収率低。ビタミンCとの同時配合で吸収率向上。酸化リスクあり。",
    },

    "DHA / EPA (Omega-3 fatty acids)": {
        "major_suppliers": ["DSM (life's DHA®, MEG-3®)", "BASF (Pronova®)", "Omega Protein (OmegaPure®)", "KD Pharma"],
        "japan_suppliers": ["日本水産 (MEGA)", "日清オイリオグループ", "三菱商事"],
        "oem_forms": ["softgel", "capsule", "powder (microencapsulated)", "emulsion"],
        "typical_grade": "Food / Pharmaceutical",
        "certifications": ["GFSI", "IFOS (5-star)", "Non-GMO", "Friend of the Sea"],
        "price_tier": "high",
        "lead_time_weeks": 6,
        "min_order_qty": "25 kg",
        "notes": "酸化管理が最重要。窒素充填・暗所保管必須。5-star IFOS 認証品が信頼性高い。",
    },

    "Collagen peptide": {
        "major_suppliers": ["Gelita (Verisol®, Fortigel®)", "Rousselot (PEPTAN®)", "Nitta Gelatin (新田ゼラチン)"],
        "japan_suppliers": ["新田ゼラチン", "宮城化学工業", "日本ハム"],
        "oem_forms": ["powder", "tablet", "capsule", "drink", "jelly"],
        "typical_grade": "Food",
        "certifications": ["Halal", "Kosher (魚由来のみ)", "Non-GMO", "BSE free"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "25 kg",
        "notes": "牛・豚・魚由来の区別が宗教・アレルゲン表示で重要。分子量と用途の整合性を確認。",
    },

    "Fructooligosaccharides (FOS)": {
        "major_suppliers": ["Beneo (Orafti® FOS)", "Cosucra (Fibruline®)", "Quantum Hi-Tech"],
        "japan_suppliers": ["明治フードテクノ", "カルピス", "大日本住友製薬"],
        "oem_forms": ["powder", "syrup", "tablet", "capsule", "drink_mix"],
        "typical_grade": "Food",
        "certifications": ["Non-GMO", "Kosher", "Halal", "Organic (一部)"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "25 kg",
        "notes": "過剰摂取でガス・膨満感あり。製品への配合量設計に注意。",
    },

    "Pectin": {
        "major_suppliers": ["CP Kelco (GENU®)", "Herbstreith & Fox", "Cargill"],
        "japan_suppliers": ["伊那食品工業", "三栄源エフ・エフ・アイ"],
        "oem_forms": ["powder", "liquid"],
        "typical_grade": "Food",
        "certifications": ["Non-GMO", "Kosher", "Halal", "Organic (一部)"],
        "price_tier": "low",
        "lead_time_weeks": 4,
        "min_order_qty": "25 kg",
        "notes": "HM/LM ペクチンで pH・カルシウム要件が異なる。用途に合わせた選定が必要。",
    },

    "Lactic acid": {
        "major_suppliers": ["Corbion (PURAC®)", "Galactic", "Musashino Chemical"],
        "japan_suppliers": ["武蔵野化学研究所", "片山化学工業研究所"],
        "oem_forms": ["liquid", "powder"],
        "typical_grade": "Food / USP",
        "certifications": ["GRAS", "Non-GMO", "Kosher", "Halal"],
        "price_tier": "low",
        "lead_time_weeks": 2,
        "min_order_qty": "200 kg (liquid)",
        "notes": "L-乳酸と D-乳酸の純度区別に注意。食品用途は L-乳酸が主流。",
    },

    "Coenzyme Q10 (Ubiquinone)": {
        "major_suppliers": ["Kaneka (Kaneka QH®, Kaneka Q10®)", "DSM", "ZMC (中国)"],
        "japan_suppliers": ["カネカ", "日清ファルマ"],
        "oem_forms": ["powder", "softgel", "capsule", "tablet"],
        "typical_grade": "Food / Pharmaceutical",
        "certifications": ["GRAS", "Non-GMO", "Kosher", "Halal", "USP"],
        "price_tier": "very_high",
        "lead_time_weeks": 6,
        "min_order_qty": "1 kg",
        "notes": "還元型 (Ubiquinol, Kaneka QH®) は酸化型より吸収が良いが高価。光・熱・酸素に弱い。",
    },

    "Hyaluronic acid": {
        "major_suppliers": ["Shiseido (HYALUFIX®)", "Kewpie (Hyabest®)", "Bloomage Biotech", "HTL Biotechnology"],
        "japan_suppliers": ["資生堂", "キューピー", "電気化学工業"],
        "oem_forms": ["powder", "capsule", "tablet", "drink"],
        "typical_grade": "Food / Cosmetic",
        "certifications": ["Non-GMO", "Kosher", "Halal"],
        "price_tier": "high",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "分子量で用途が異なる（高分子: 保湿、低分子: 浸透性）。発酵由来品が主流。",
    },

    "Astaxanthin": {
        "major_suppliers": ["AstaReal (富士化学工業)", "Cyanotech (BioAstin®)", "Algatechnologies", "Valensa"],
        "japan_suppliers": ["富士化学工業 (AstaReal®)", "大洋香料"],
        "oem_forms": ["softgel", "capsule", "powder (oil-based)", "emulsion"],
        "typical_grade": "Food",
        "certifications": ["GRAS", "Non-GMO", "Halal", "Kosher"],
        "price_tier": "very_high",
        "lead_time_weeks": 6,
        "min_order_qty": "1 kg",
        "notes": "ヘマトコッカス藻由来が最高品質。光・熱・酸素で急速に劣化。暗所・低温保管必須。",
    },

    "Grape seed proanthocyanidins (OPC)": {
        "major_suppliers": ["Indena (Leucoselect®)", "Natex", "Polyphenolics (MegaNatural®)"],
        "japan_suppliers": ["三栄源エフ・エフ・アイ", "長谷川香料"],
        "oem_forms": ["powder", "capsule", "tablet"],
        "typical_grade": "Standardized Extract",
        "certifications": ["Non-GMO", "Kosher", "Halal"],
        "price_tier": "high",
        "lead_time_weeks": 6,
        "min_order_qty": "1 kg",
        "notes": "OPC 95% 標準化品が主流。フラン化合物の副産物に注意（高品質サプライヤー選定推奨）。",
    },

    "Black vinegar (Kurozu)": {
        "major_suppliers": ["Mizkan Holdings", "Iio Jozo (飯尾醸造)", "Kakuida (坂元醸造)"],
        "japan_suppliers": ["ミツカン", "飯尾醸造", "坂元醸造", "タマノイ酢"],
        "oem_forms": ["liquid", "powder", "capsule", "tablet", "drink"],
        "typical_grade": "Food",
        "certifications": ["有機JAS (一部)", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "200 L (liquid)",
        "notes": "伝統的な壺仕込みが付加価値高い。アミノ酸含有量の規格確認が重要。",
    },

    "Inulin": {
        "major_suppliers": ["Beneo (Orafti® Inulin)", "Cosucra", "Cargill (Oliggo-Fiber®)"],
        "japan_suppliers": ["明治フードテクノ", "日本甜菜製糖"],
        "oem_forms": ["powder", "syrup"],
        "typical_grade": "Food",
        "certifications": ["Non-GMO", "Kosher", "Halal", "Organic (一部)"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "25 kg",
        "notes": "チコリ由来イヌリンが主流。重合度（DP）で機能・甘味・粘度が変わる。",
    },

    "Caffeine": {
        "major_suppliers": ["BASF", "Aarti Industries", "Spectrum Chemicals"],
        "japan_suppliers": ["林純薬工業", "東京化成工業"],
        "oem_forms": ["powder", "tablet", "capsule", "drink"],
        "typical_grade": "Food / USP",
        "certifications": ["USP", "JP", "Non-GMO"],
        "price_tier": "low",
        "lead_time_weeks": 2,
        "min_order_qty": "25 kg",
        "notes": "高用量製品は医薬品境界線に注意。エナジードリンクでは上限表示・警告文が必要。",
    },

    "Green tea": {
        "major_suppliers": ["Taiyo Green Power (Sunphenon®)", "Indena", "Finzelberg"],
        "japan_suppliers": ["太陽化学 (Sunphenon®)", "伊藤園", "丸善製薬"],
        "oem_forms": ["powder", "extract", "capsule", "tablet", "tea_bag", "drink"],
        "typical_grade": "Food / Standardized Extract",
        "certifications": ["Organic (一部)", "Non-GMO", "Kosher", "Halal"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg (extract)",
        "notes": "カテキン標準化品（EGCG 含量）を確認。高濃度エキスは肝毒性リスクあり。",
    },

    "Whey protein": {
        "major_suppliers": ["Fonterra (New Zealand)", "Arla Foods (Denmark)", "Hilmar Ingredients", "Glanbia"],
        "japan_suppliers": ["森永乳業", "明治", "雪印メグミルク"],
        "oem_forms": ["powder", "drink", "bar", "capsule"],
        "typical_grade": "Food",
        "certifications": ["NSF Certified for Sport", "Informed Sport", "Non-GMO", "Halal (一部)"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "25 kg",
        "notes": "乳アレルゲン表示必須。WPI/WPC/WPH の純度差に注意。",
    },

    "Soy protein": {
        "major_suppliers": ["ADM (Ardex®)", "DuPont (SUPRO®)", "Kerry Group"],
        "japan_suppliers": ["不二製油", "昭和産業", "日清オイリオ"],
        "oem_forms": ["powder", "isolate", "concentrate", "textured"],
        "typical_grade": "Food",
        "certifications": ["Non-GMO (IP管理)", "Kosher", "Halal"],
        "price_tier": "low",
        "lead_time_weeks": 4,
        "min_order_qty": "25 kg",
        "notes": "大豆アレルゲン表示必須。遺伝子組換えの IP 管理体制確認が重要。",
    },

    "Collagen peptide": {
        "major_suppliers": ["Gelita (Verisol®, Fortigel®)", "Rousselot (PEPTAN®)", "Nitta Gelatin"],
        "japan_suppliers": ["新田ゼラチン", "宮城化学工業"],
        "oem_forms": ["powder", "tablet", "capsule", "drink", "jelly"],
        "typical_grade": "Food",
        "certifications": ["Halal", "Kosher (魚由来のみ)", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "25 kg",
        "notes": "牛・豚・魚由来の区別が宗教・アレルゲン面で重要。",
    },

    "Dietary fiber": {
        "major_suppliers": ["Tate & Lyle (Promitor®)", "Beneo", "Cargill", "Ingredion"],
        "japan_suppliers": ["松谷化学工業", "江崎グリコ (難消化性デキストリン)"],
        "oem_forms": ["powder", "syrup", "tablet", "drink_mix"],
        "typical_grade": "Food",
        "certifications": ["Non-GMO", "Kosher", "Halal"],
        "price_tier": "low",
        "lead_time_weeks": 4,
        "min_order_qty": "25 kg",
        "notes": "種類（難消化性デキストリン・イヌリン・psyllium等）で機能が大きく異なる。",
    },

    "Germinated brown rice": {
        "major_suppliers": ["BioActives Japan", "Nuruk Korea", "発芽玄米専門メーカー各社"],
        "japan_suppliers": ["東洋ライス", "秋田食品", "サタケ"],
        "oem_forms": ["whole_grain", "powder", "puff", "drink"],
        "typical_grade": "Food",
        "certifications": ["有機JAS", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "25 kg",
        "notes": "発芽条件（温度・水分・時間）でGABA含有量が変動。品質規格の確認が重要。",
    },

    "Oats": {
        "major_suppliers": ["Quaker Oats (PepsiCo)", "Bob's Red Mill", "Richardson Milling"],
        "japan_suppliers": ["日本食品製造", "クエーカー・ジャパン"],
        "oem_forms": ["whole_oat", "rolled", "powder", "bran"],
        "typical_grade": "Food",
        "certifications": ["GF certified (グルテンフリー品)", "Organic", "Non-GMO"],
        "price_tier": "low",
        "lead_time_weeks": 2,
        "min_order_qty": "25 kg",
        "notes": "グルテンフリー標榜する場合は専用ライン製品を選択。β-グルカン含量を規格化。",
    },

    "Cow's milk": {
        "major_suppliers": ["Fonterra", "Arla", "FrieslandCampina"],
        "japan_suppliers": ["雪印メグミルク", "森永乳業", "明治"],
        "oem_forms": ["liquid", "powder", "concentrate"],
        "typical_grade": "Food",
        "certifications": ["Non-GMO"],
        "price_tier": "low",
        "lead_time_weeks": 2,
        "min_order_qty": "200 L (液体)",
        "notes": "乳アレルゲン表示必須。放射線検査・残留農薬検査体制を確認。",
    },

    "Lactose": {
        "major_suppliers": ["Fonterra", "Arla", "DFE Pharma"],
        "japan_suppliers": ["雪印メグミルク", "林純薬工業"],
        "oem_forms": ["powder"],
        "typical_grade": "Food / Pharmaceutical",
        "certifications": ["Ph.Eur.", "USP", "JP"],
        "price_tier": "low",
        "lead_time_weeks": 2,
        "min_order_qty": "25 kg",
        "notes": "乳糖不耐症表示に注意。医薬品グレードは安定性が高い。",
    },

    # ── Enzymes ──────────────────────────────────────────────────────────────

    "Protease": {
        "major_suppliers": ["Novozymes (Neutrase®, Alcalase®)", "DSM (Maxazyme®)", "AB Enzymes"],
        "japan_suppliers": ["天野エンザイム", "長瀬産業"],
        "oem_forms": ["powder", "liquid"],
        "typical_grade": "Food",
        "certifications": ["GRAS", "Halal", "Kosher", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "至適 pH・温度がサプライヤー品種により異なる。活性単位（AU, HUT等）の確認必須。",
    },

    "Lactase (beta-galactosidase)": {
        "major_suppliers": ["DSM (Maxilact®)", "Chr. Hansen", "Novozymes"],
        "japan_suppliers": ["天野エンザイム", "長瀬産業"],
        "oem_forms": ["powder", "liquid"],
        "typical_grade": "Food",
        "certifications": ["GRAS (21 CFR 184.1027)", "Halal", "Kosher"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "乳製品処理と supplement 配合で要求活性単位が異なる。",
    },

    "Amylase": {
        "major_suppliers": ["Novozymes (Termamyl®, BAN®)", "DSM", "AB Enzymes"],
        "japan_suppliers": ["天野エンザイム", "長瀬産業", "キッコーマン"],
        "oem_forms": ["powder", "liquid"],
        "typical_grade": "Food",
        "certifications": ["GRAS", "Halal", "Kosher"],
        "price_tier": "low",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "α-アミラーゼ/グルコアミラーゼ/β-アミラーゼの選択が用途によって異なる。",
    },

    "Lipase": {
        "major_suppliers": ["Novozymes (Palatase®, Lipozyme®)", "DSM (Palatase®)", "Amano Enzyme"],
        "japan_suppliers": ["天野エンザイム", "長瀬産業"],
        "oem_forms": ["powder", "liquid"],
        "typical_grade": "Food",
        "certifications": ["GRAS", "Halal", "Kosher"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "脂質加水分解の特異性（sn-1,3 選択性等）を確認。",
    },

    "Phytase": {
        "major_suppliers": ["Novozymes (Ronozyme®)", "BASF (Natuphos®)", "DSM (PHYZYME®)"],
        "japan_suppliers": ["天野エンザイム", "長瀬産業"],
        "oem_forms": ["powder", "liquid", "granule"],
        "typical_grade": "Food / Feed",
        "certifications": ["GRAS", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "フィチン酸分解でミネラル吸収を高める。pH 安定性・熱安定性の確認が重要。",
    },

    "Asparaginase": {
        "major_suppliers": ["Novozymes (Acrylaway®)", "DSM"],
        "japan_suppliers": ["天野エンザイム"],
        "oem_forms": ["powder", "liquid"],
        "typical_grade": "Food",
        "certifications": ["EU approved", "Non-GMO"],
        "price_tier": "high",
        "lead_time_weeks": 6,
        "min_order_qty": "1 kg",
        "notes": "アクリルアミド低減目的（ベーカリー・スナック）。EU/US で承認済み。日本は個別許可制。",
    },

    "Cellulase": {
        "major_suppliers": ["Novozymes (Celluclast®)", "DSM", "AB Enzymes (Rohament® CL)"],
        "japan_suppliers": ["天野エンザイム", "長瀬産業"],
        "oem_forms": ["powder", "liquid"],
        "typical_grade": "Food",
        "certifications": ["GRAS", "Halal", "Kosher"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "セルロース系食物繊維の分解・植物細胞壁崩壊に使用。",
    },

    "Transglutaminase (TGase)": {
        "major_suppliers": ["Ajinomoto (Activa® series)", "Yiming Biological", "TFP (Transglutaminase Food Products)"],
        "japan_suppliers": ["味の素", "天野エンザイム"],
        "oem_forms": ["powder"],
        "typical_grade": "Food",
        "certifications": ["GRAS (GRN 299)", "Halal", "Kosher"],
        "price_tier": "high",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "タンパク質架橋で食感改良。Activa® TG-M, TG-F, TG-B 等、用途により選択。",
    },

    # ── Microbes ──────────────────────────────────────────────────────────────

    "Lactobacillus": {
        "major_suppliers": ["Chr. Hansen", "DuPont Nutrition & Biosciences (Danisco)", "Lallemand Health Solutions", "BioGaia"],
        "japan_suppliers": ["ヤクルト本社", "明治", "キリンホールディングス", "森永乳業"],
        "oem_forms": ["powder (freeze-dried)", "capsule", "tablet", "drink", "yogurt_base"],
        "typical_grade": "Food / Probiotic",
        "certifications": ["GRAS/QPS", "GMP", "NSF", "Informed Sport"],
        "price_tier": "high",
        "lead_time_weeks": 8,
        "min_order_qty": "100g (freeze-dried)",
        "notes": "株レベルで機能・安全性が異なる。菌数保証（CFU/g）と shelf-life を確認。",
    },

    "Bifidobacterium": {
        "major_suppliers": ["Chr. Hansen", "DuPont (Howaru®)", "Morinaga Milk Industry (森永乳業)", "Probi"],
        "japan_suppliers": ["森永乳業", "ヤクルト本社", "明治"],
        "oem_forms": ["powder (freeze-dried)", "capsule", "tablet", "drink"],
        "typical_grade": "Food / Probiotic",
        "certifications": ["GRAS/QPS", "GMP"],
        "price_tier": "high",
        "lead_time_weeks": 8,
        "min_order_qty": "100g (freeze-dried)",
        "notes": "酸素感受性が高い。マイクロカプセル化や N2 封入が shelf-life 向上に必要。",
    },

    "Yeast (Saccharomyces cerevisiae)": {
        "major_suppliers": ["Lallemand", "Angel Yeast", "Lesaffre", "AB Mauri"],
        "japan_suppliers": ["オリエンタル酵母工業", "アサヒグループ食品"],
        "oem_forms": ["fresh_yeast", "dry_yeast", "powder", "extract", "autolysate"],
        "typical_grade": "Food",
        "certifications": ["Non-GMO", "Organic (一部)", "Kosher", "Halal"],
        "price_tier": "low",
        "lead_time_weeks": 2,
        "min_order_qty": "25 kg (dry)",
        "notes": "製パン用・醸造用・栄養補助用で株・グレードが異なる。酵母エキスは別規格。",
    },

    "Aspergillus oryzae (Koji)": {
        "major_suppliers": ["天野エンザイム", "秋田今野商店", "糀屋本店"],
        "japan_suppliers": ["天野エンザイム", "秋田今野商店", "ビオック"],
        "oem_forms": ["dried_koji", "koji_starter (seed koji)", "extract"],
        "typical_grade": "Food / Traditional",
        "certifications": ["Non-GMO", "有機JAS (一部)"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg (seed koji)",
        "notes": "種麹の選択で酵素プロファイルが変わる。アフラトキシン管理が必須。",
    },

    "Bacillus subtilis var. natto": {
        "major_suppliers": ["成田食品 (ナットウキナーゼ含む)", "Japan Bio Science Lab (JBSL)", "宮城野納豆製造所"],
        "japan_suppliers": ["成田食品", "Japan Bio Science Lab", "コスモ食品"],
        "oem_forms": ["natto", "freeze-dried_powder", "capsule"],
        "typical_grade": "Food / Traditional",
        "certifications": ["有機JAS (一部)", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 6,
        "min_order_qty": "100g (freeze-dried)",
        "notes": "ナットウキナーゼ活性（FU/g）の規格が重要。ビタミン K2（MK-7）との混合品注意。",
    },

    "Lactobacillus plantarum": {
        "major_suppliers": ["Chr. Hansen", "Lallemand", "Probi (PROBI® DIGESTIS)"],
        "japan_suppliers": ["キリンホールディングス (KW乳酸菌)", "明治"],
        "oem_forms": ["powder (freeze-dried)", "capsule", "drink"],
        "typical_grade": "Food / Probiotic",
        "certifications": ["GRAS/QPS", "GMP"],
        "price_tier": "high",
        "lead_time_weeks": 8,
        "min_order_qty": "100g",
        "notes": "Lp299v 等の特定株が研究・商品化で広く使用。株ライセンス確認が必要な場合あり。",
    },

    "Leuconostoc mesenteroides": {
        "major_suppliers": ["Chr. Hansen", "DuPont", "Lallemand"],
        "japan_suppliers": ["明治", "カルピス"],
        "oem_forms": ["culture_starter", "freeze-dried_powder"],
        "typical_grade": "Food",
        "certifications": ["QPS (EFSA)", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 6,
        "min_order_qty": "100g",
        "notes": "キムチ・ザワークラウト発酵用スターター。デキストランやマンニトール生産に使用。",
    },

    "Acetobacter aceti": {
        "major_suppliers": ["Lallemand", "Chr. Hansen", "ミツカン (内製)"],
        "japan_suppliers": ["ミツカン", "タマノイ酢", "坂元醸造"],
        "oem_forms": ["liquid_culture", "starter"],
        "typical_grade": "Food / Fermentation",
        "certifications": ["Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "研究用サンプル要問合せ",
        "notes": "酢酸発酵専用。エタノール濃度・pH・酸素供給が産酸速度に影響。",
    },

    "Streptococcus thermophilus": {
        "major_suppliers": ["Chr. Hansen", "DuPont (Danisco)", "Sacco System"],
        "japan_suppliers": ["明治", "森永乳業", "雪印メグミルク"],
        "oem_forms": ["culture_starter (freeze-dried)", "liquid"],
        "typical_grade": "Food",
        "certifications": ["GRAS (21 CFR 184)", "QPS (EFSA)"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "研究用サンプル要問合せ",
        "notes": "ヨーグルト・チーズ製造の必須スターター。Lactobacillus との共培養が一般的。",
    },

    # ── Batch 2 Ingredients ──────────────────────────────────────────────────

    "Resveratrol": {
        "major_suppliers": ["Evolva", "DSM", "Sabinsa", "Shaanxi Huike Botanical Development"],
        "japan_suppliers": ["長谷川香料", "三菱商事ライフサイエンス", "Evolva Japan"],
        "oem_forms": ["powder", "capsule", "softgel", "tablet"],
        "typical_grade": "Food / Standardized Extract (98%)",
        "certifications": ["Non-GMO", "Kosher", "Halal", "GRAS (一部)"],
        "price_tier": "high",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "ポリゴヌム・コスピダタム由来が主流。光・熱に不安定。遮光保管必須。",
    },

    "Quercetin": {
        "major_suppliers": ["Quercegen Pharma", "Sigma-Aldrich", "Shaanxi Guanjie Technology", "Indena"],
        "japan_suppliers": ["三菱商事ライフサイエンス", "太陽化学", "長谷川香料"],
        "oem_forms": ["powder", "capsule", "tablet"],
        "typical_grade": "Food / Standardized Extract (95-98%)",
        "certifications": ["Non-GMO", "Kosher", "Halal"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "水溶性低い。フィトソームや PLGA 封入で吸収性改善。ソフォラ・タマネギ由来。",
    },

    "Alpha-lipoic acid (ALA)": {
        "major_suppliers": ["BASF", "Evonik", "Zhejiang Zhongxin Biotechnology", "Biopharma"],
        "japan_suppliers": ["BASF Japan", "住友ファーマフード＆ケミカル", "三菱商事ライフサイエンス"],
        "oem_forms": ["powder", "capsule", "tablet", "softgel"],
        "typical_grade": "Food / Pharmaceutical",
        "certifications": ["USP", "EP", "Non-GMO", "Kosher"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "5 kg",
        "notes": "ラセミ体（R/S 混合）が一般的。R-ALA は高価だが生物活性が高い。熱に弱い。",
    },

    "L-Carnitine": {
        "major_suppliers": ["Lonza (Carnipure®)", "BASF", "Sigma-Tau (Sigma-Aldrich)", "HuangGang HuaYang"],
        "japan_suppliers": ["Lonza Japan (Carnipure®)", "協和発酵バイオ", "武田薬品工業"],
        "oem_forms": ["powder", "capsule", "tablet", "drink_mix", "liquid"],
        "typical_grade": "Food / USP",
        "certifications": ["GRAS (GRN 56)", "USP", "JP", "Halal", "Kosher", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "5 kg",
        "notes": "Carnipure® ブランドが品質面で信頼性高。L-酒石酸塩形態が安定性に優れる。",
    },

    "Vitamin D3 (Cholecalciferol)": {
        "major_suppliers": ["DSM (ROVIMIX® D3)", "BASF", "Zhejiang Garden Biochemical", "Fermenta Biotech"],
        "japan_suppliers": ["DSM Japan (ROVIMIX® D3)", "武田薬品工業", "三菱商事フードテック"],
        "oem_forms": ["powder", "oil", "capsule", "softgel", "tablet", "gummy"],
        "typical_grade": "Food / USP / EP",
        "certifications": ["USP", "EP", "JP", "Halal", "Kosher", "Non-GMO"],
        "price_tier": "low",
        "lead_time_weeks": 3,
        "min_order_qty": "1 kg",
        "notes": "羊毛脂（ラノリン）由来が主流。ビーガン向けにはリケン（藻類）由来品も存在。",
    },

    "Vitamin E (Tocopherol)": {
        "major_suppliers": ["DSM", "BASF", "Archer Daniels Midland (ADM)", "Cognis"],
        "japan_suppliers": ["DSM Japan", "BASF Japan", "太陽化学"],
        "oem_forms": ["oil", "powder", "capsule", "softgel", "tablet"],
        "typical_grade": "Food / USP / EP",
        "certifications": ["USP", "EP", "JP", "Non-GMO", "Natural (d-alpha)"],
        "price_tier": "low",
        "lead_time_weeks": 3,
        "min_order_qty": "10 kg",
        "notes": "天然型（d-alpha）と合成型（dl-alpha）で生物活性が約2倍異なる。",
    },

    "Vitamin B12 (Cyanocobalamin)": {
        "major_suppliers": ["DSM", "BASF", "Hebei Huarong Pharmaceutical", "Sanofi"],
        "japan_suppliers": ["DSM Japan", "武田薬品工業", "三菱商事フードテック"],
        "oem_forms": ["powder", "capsule", "tablet", "sublingual"],
        "typical_grade": "Food / USP / EP",
        "certifications": ["USP", "EP", "JP", "Halal", "Kosher"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "100 g",
        "notes": "シアノコバラミンが安価で安定。メチルコバラミンは神経系に直接利用可能。",
    },

    "Folic acid": {
        "major_suppliers": ["DSM (QUALI-FOLIC®)", "BASF", "Zhejiang Shengda Bio-pharm", "Jiangxi Tianxin Pharmaceutical"],
        "japan_suppliers": ["DSM Japan", "武田薬品工業", "三菱商事フードテック"],
        "oem_forms": ["powder", "capsule", "tablet", "premix"],
        "typical_grade": "Food / USP / EP",
        "certifications": ["USP", "EP", "JP", "Halal", "Kosher", "Non-GMO"],
        "price_tier": "low",
        "lead_time_weeks": 3,
        "min_order_qty": "1 kg",
        "notes": "葉酸（Folic acid）と5-MTHF（活性型）で代謝経路が異なる。MTHFR 遺伝子変異者には活性型が有効。",
    },

    "Calcium": {
        "major_suppliers": ["ICL Group", "Omya", "Huber Engineered Materials", "Balchem (TRAACS®)"],
        "japan_suppliers": ["太陽化学", "富田製薬", "林純薬工業"],
        "oem_forms": ["powder", "capsule", "tablet", "gummy", "chewable"],
        "typical_grade": "Food / USP / JP",
        "certifications": ["USP", "JP", "Halal", "Kosher", "Non-GMO"],
        "price_tier": "low",
        "lead_time_weeks": 2,
        "min_order_qty": "25 kg",
        "notes": "炭酸Ca・クエン酸Ca・乳酸Caで吸収率が異なる。ビタミンD3との配合が吸収促進に有効。",
    },

    "Selenium": {
        "major_suppliers": ["Alltech (Sel-Plex®)", "Lallemand (Selemax®)", "Sabinsa", "DSM"],
        "japan_suppliers": ["Alltech Japan", "三菱商事ライフサイエンス", "太陽化学"],
        "oem_forms": ["powder", "capsule", "tablet", "yeast"],
        "typical_grade": "Food / Pharmaceutical",
        "certifications": ["GRAS", "Non-GMO", "Halal", "Kosher"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "酵母セレン（有機セレン）が吸収性・安全性で優位。上限量（400μg/日）に注意。",
    },

    "Beta-glucan": {
        "major_suppliers": ["Koninklijke DSM", "Cargill (OatWell®)", "Naturex", "Kerry Group"],
        "japan_suppliers": ["日本製粉", "太陽化学", "三菱商事ライフサイエンス"],
        "oem_forms": ["powder", "capsule", "tablet", "functional_food"],
        "typical_grade": "Food",
        "certifications": ["GRAS", "Non-GMO", "Kosher", "Halal"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "5 kg",
        "notes": "オーツ由来（β1,3/1,4型）と酵母由来（β1,3/1,6型）で免疫・コレステロール作用が異なる。",
    },

    "Galactooligosaccharides (GOS)": {
        "major_suppliers": ["Clasado (Bimuno®)", "Yakult Pharmaceutical", "FrieslandCampina (Vivinal® GOS)"],
        "japan_suppliers": ["ヤクルト薬品工業", "太陽化学", "雪印メグミルク"],
        "oem_forms": ["powder", "syrup", "capsule"],
        "typical_grade": "Food",
        "certifications": ["GRAS (GRN 236)", "Non-GMO", "Kosher", "Halal"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "5 kg",
        "notes": "乳糖からラクターゼにより酵素合成。ビフィズス菌選択的増殖。粉末型が安定。",
    },

    "Soy isoflavones": {
        "major_suppliers": ["Natunola", "Archer Daniels Midland (ADM)", "Solae", "Indena"],
        "japan_suppliers": ["不二製油", "太陽化学", "三菱商事フードテック"],
        "oem_forms": ["powder", "capsule", "tablet"],
        "typical_grade": "Food / Standardized Extract (40-80%)",
        "certifications": ["Non-GMO (認証品あり)", "Kosher", "Halal"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "ゲニステイン・ダイゼイン・グリシテイン混合。エストロゲン様作用に注意（ホルモン感受性疾患）。",
    },

    "Lactoferrin": {
        "major_suppliers": ["FrieslandCampina (Lactoferrin)", "Morinaga Milk Industry", "Tatua"],
        "japan_suppliers": ["森永乳業 (ラクトフェリン)", "雪印メグミルク", "太陽化学"],
        "oem_forms": ["powder", "capsule", "tablet", "functional_food"],
        "typical_grade": "Food / Pharmaceutical",
        "certifications": ["GRAS (GRN 672)", "Non-GMO", "Kosher", "Halal"],
        "price_tier": "very_high",
        "lead_time_weeks": 6,
        "min_order_qty": "500 g",
        "notes": "牛乳由来タンパク（抗菌・免疫）。熱に弱いため低温加工必須。腸溶コーティングが有効。",
    },

    "Casein": {
        "major_suppliers": ["FrieslandCampina", "Fonterra", "Tatua", "Arla Foods Ingredients"],
        "japan_suppliers": ["森永乳業", "雪印メグミルク", "太陽化学"],
        "oem_forms": ["powder", "capsule", "functional_food"],
        "typical_grade": "Food",
        "certifications": ["Non-GMO", "Kosher", "Halal"],
        "price_tier": "low",
        "lead_time_weeks": 3,
        "min_order_qty": "25 kg",
        "notes": "ミセルカゼイン（MCC）が消化ゆっくりで就寝前摂取に最適。乳アレルゲン表示必須。",
    },

    "Lutein": {
        "major_suppliers": ["Kemin Industries (FloraGLO®)", "OmniActive Health Technologies (LuteMax®)", "Naturex"],
        "japan_suppliers": ["太陽化学 (FloraGLO®)", "三菱商事ライフサイエンス"],
        "oem_forms": ["powder", "softgel", "capsule", "tablet"],
        "typical_grade": "Food / Standardized Extract (5-20%)",
        "certifications": ["GRAS (GRN 140)", "Non-GMO", "Kosher", "Halal"],
        "price_tier": "high",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "マリーゴールド花由来。脂溶性のためオイル懸濁液や乳化製剤が吸収に有利。",
    },

    "Nattokinase": {
        "major_suppliers": ["Japan Bio Science Laboratory (JBSL)", "Contek Life Science", "Daiwa Pharmaceutical"],
        "japan_suppliers": ["大和薬品 (NK ナットウキナーゼ)", "日本バイオサイエンスラボラトリー"],
        "oem_forms": ["powder", "capsule", "tablet"],
        "typical_grade": "Food / Standardized (FU/g)",
        "certifications": ["Non-GMO", "Kosher", "Halal"],
        "price_tier": "high",
        "lead_time_weeks": 6,
        "lead_time_weeks": 4,
        "min_order_qty": "500 g",
        "notes": "活性単位（FU: フィブリン溶解単位）で規格化。ワルファリン服用者は禁忌。腸溶コーティング推奨。",
    },

    "Spirulina": {
        "major_suppliers": ["DIC (Spirulina)","Earthrise Nutritionals", "Cyanotech (Hawaiian Spirulina®)"],
        "japan_suppliers": ["DIC (スピルリナ)", "タマ生化学", "東洋新薬"],
        "oem_forms": ["powder", "tablet", "capsule"],
        "typical_grade": "Food",
        "certifications": ["Organic (一部)", "Non-GMO", "Kosher", "Halal"],
        "price_tier": "low",
        "lead_time_weeks": 3,
        "min_order_qty": "5 kg",
        "notes": "重金属汚染リスクあり。生産地・検査証明書の確認必須。藻臭が強い。",
    },

    "Chlorella": {
        "major_suppliers": ["Sun Chlorella", "Taiwan Chlorella Manufacturing", "Yaeyama Shokusan"],
        "japan_suppliers": ["サン・クロレラ", "八重山殖産", "クロレラ工業"],
        "oem_forms": ["powder", "tablet", "capsule"],
        "typical_grade": "Food",
        "certifications": ["Organic (一部)", "Non-GMO", "Kosher", "Halal"],
        "price_tier": "low",
        "lead_time_weeks": 3,
        "min_order_qty": "5 kg",
        "notes": "細胞壁破砕処理品が消化吸収に優れる。重金属・マイコトキシン検査必須。",
    },

    "Gamma-linolenic acid (GLA)": {
        "major_suppliers": ["Efamol (EPO)", "Natunola (Borage oil)", "Camelina Gold"],
        "japan_suppliers": ["太陽化学", "三菱商事ライフサイエンス"],
        "oem_forms": ["oil", "softgel", "capsule"],
        "typical_grade": "Food",
        "certifications": ["Non-GMO", "Kosher", "Halal"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "5 kg",
        "notes": "月見草・ボラージ・黒スグリ由来。酸化しやすいため不活性ガス充填・遮光保管必須。",
    },

    "Black ginger (Kaempferia parviflora)": {
        "major_suppliers": ["Sabinsa (KaempMax™)", "Oryza Oil & Fat Chemical", "Thai Herbs"],
        "japan_suppliers": ["オリザ油化 (ブラックジンジャー)", "太陽化学", "東洋新薬"],
        "oem_forms": ["powder", "extract", "capsule", "tablet"],
        "typical_grade": "Food / Standardized Extract",
        "certifications": ["Non-GMO", "Halal"],
        "price_tier": "high",
        "lead_time_weeks": 6,
        "min_order_qty": "1 kg",
        "notes": "タイ産が品質安定。ポリメトキシフラボノイド含量で規格化。",
    },

    "N-Acetyl Cysteine (NAC)": {
        "major_suppliers": ["BASF", "Zambon", "Nippon Rika", "Shandong Biochemical"],
        "japan_suppliers": ["BASF Japan", "日本理化薬品", "三菱商事ライフサイエンス"],
        "oem_forms": ["powder", "capsule", "tablet", "effervescent"],
        "typical_grade": "Food / USP / EP",
        "certifications": ["USP", "EP", "Kosher", "Halal"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "5 kg",
        "notes": "硫黄臭があり製剤化に工夫が必要。FDAが一部サプリ用途に懸念（要確認）。酸化防止剤として使用可。",
    },

    "Berberine": {
        "major_suppliers": ["Shaanxi Huike Botanical Development", "Xi'an Sgonek Biological Technology", "Natupharma"],
        "japan_suppliers": ["東洋新薬", "太陽化学", "長谷川香料"],
        "oem_forms": ["powder", "capsule", "tablet"],
        "typical_grade": "Food / Standardized Extract (97-98%)",
        "certifications": ["Non-GMO", "Kosher", "Halal"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "薬物相互作用（CYP3A4）に注意。日本では医薬品扱いの場合あり（要規制確認）。",
    },

    "Psyllium husk": {
        "major_suppliers": ["Psyllium Labs", "Emetris (India)", "NOW Foods (raw material)", "ICP (India)"],
        "japan_suppliers": ["太陽化学", "三菱商事ライフサイエンス", "日清ファルマ"],
        "oem_forms": ["powder", "capsule", "functional_food"],
        "typical_grade": "Food / USP",
        "certifications": ["USP", "Non-GMO", "Kosher", "Halal", "Organic (一部)"],
        "price_tier": "low",
        "lead_time_weeks": 3,
        "min_order_qty": "25 kg",
        "notes": "インド産が主流（世界供給の85%）。水分で膨張するため十分な水分と共に摂取。",
    },

    "Trehalose": {
        "major_suppliers": ["Hayashibara (TREHA®)", "Cargill"],
        "japan_suppliers": ["林原 (TREHA®)", "三菱商事フードテック"],
        "oem_forms": ["powder", "granule", "syrup"],
        "typical_grade": "Food",
        "certifications": ["GRAS (GRN 36)", "Halal", "Kosher", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 3,
        "min_order_qty": "10 kg",
        "notes": "林原が世界最大サプライヤー。食品保護・乾燥保護用途。日本での普及率高い。",
    },

    "Ergothioneine": {
        "major_suppliers": ["Tetrahedron (EGT)","Mironova Labs", "Blue California"],
        "japan_suppliers": ["三菱ケミカル", "キリンホールディングス (キリン EGT)"],
        "oem_forms": ["powder", "capsule", "tablet"],
        "typical_grade": "Food",
        "certifications": ["GRAS (GRN 702)", "Non-GMO", "Kosher"],
        "price_tier": "very_high",
        "lead_time_weeks": 8,
        "min_order_qty": "100 g",
        "notes": "酵母・菌類由来。長寿ビタミン候補として注目。非常に高価。発酵生産品が増加中。",
    },

    "Spermidine": {
        "major_suppliers": ["Longevity Labs (spermidineLIFE®)", "Zhejiang Shengda", "TCI Chemicals"],
        "japan_suppliers": ["長寿研究所", "三菱商事ライフサイエンス"],
        "oem_forms": ["powder", "capsule", "tablet"],
        "typical_grade": "Food",
        "certifications": ["Non-GMO", "Kosher"],
        "price_tier": "very_high",
        "lead_time_weeks": 6,
        "min_order_qty": "100 g",
        "notes": "小麦胚芽由来が一般的。オートファジー誘導で注目。非常に高価。",
    },

    "Lactobacillus acidophilus": {
        "major_suppliers": ["Chr. Hansen", "DuPont (Danisco)", "Lallemand", "IFF Health"],
        "japan_suppliers": ["協和発酵バイオ", "森永乳業", "Lallemand Japan"],
        "oem_forms": ["powder (freeze-dried)", "capsule", "tablet", "sachet"],
        "typical_grade": "Food / Probiotic",
        "certifications": ["GRAS", "QPS (EFSA)", "Non-GMO", "Halal", "Kosher"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "500 g",
        "notes": "CFU/g で規格化。保存条件（冷蔵 or 室温）の選択が重要。酸耐性・胆汁耐性が菌株で異なる。",
    },

    "Lactobacillus rhamnosus GG (LGG)": {
        "major_suppliers": ["IFF Health (ATCC 53103)", "Chr. Hansen", "Valio"],
        "japan_suppliers": ["IFF Japan", "太陽化学"],
        "oem_forms": ["powder (freeze-dried)", "capsule", "sachet"],
        "typical_grade": "Food / Probiotic",
        "certifications": ["GRAS (GRN 679)", "QPS (EFSA)", "Non-GMO"],
        "price_tier": "high",
        "lead_time_weeks": 6,
        "min_order_qty": "100 g",
        "notes": "世界最多研究菌株のひとつ。特許保護あり（IFF）。腸管定着性が高い。",
    },

    "Bifidobacterium longum": {
        "major_suppliers": ["Chr. Hansen", "DuPont (Danisco)", "Morinaga Milk Industry", "IFF Health"],
        "japan_suppliers": ["森永乳業 (BB536)", "協和発酵バイオ", "ヤクルト薬品工業"],
        "oem_forms": ["powder (freeze-dried)", "capsule", "sachet"],
        "typical_grade": "Food / Probiotic",
        "certifications": ["GRAS", "QPS (EFSA)", "Non-GMO", "Halal", "Kosher"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "500 g",
        "notes": "森永BB536が世界的に有名。腸内での生存率が高い。乳幼児腸内菌叢の主要菌。",
    },

    "Lactobacillus casei Shirota": {
        "major_suppliers": ["Yakult Honsha (独占)"],
        "japan_suppliers": ["ヤクルト本社"],
        "oem_forms": ["fermented_milk (ヤクルト)", "liquid"],
        "typical_grade": "Food / Probiotic",
        "certifications": ["GRAS (申請中)", "Non-GMO"],
        "price_tier": "high",
        "lead_time_weeks": 8,
        "min_order_qty": "要問合せ",
        "notes": "ヤクルト本社が独占管理。OEM原料供給は限定的。代替菌株の検討が現実的。",
    },

    "Clostridium butyricum (Miyairi 588)": {
        "major_suppliers": ["Miyarisan Pharmaceutical (宮入菌)"],
        "japan_suppliers": ["宮入製薬"],
        "oem_forms": ["capsule (宮入菌製剤)", "tablet"],
        "typical_grade": "Food / Pharmaceutical",
        "certifications": ["JP (腸内細菌製剤として)"],
        "price_tier": "high",
        "lead_time_weeks": 6,
        "min_order_qty": "要問合せ",
        "notes": "宮入製薬が独占。酪酸産生菌として腸管上皮保護に有効。芽胞形成で安定性高い。",
    },

    "Pediococcus acidilactici": {
        "major_suppliers": ["Lallemand", "Chr. Hansen", "DuPont (Danisco)"],
        "japan_suppliers": ["Lallemand Japan", "太陽化学"],
        "oem_forms": ["powder (freeze-dried)", "capsule"],
        "typical_grade": "Food / Probiotic",
        "certifications": ["GRAS", "QPS (EFSA)", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "500 g",
        "notes": "バクテリオシン（ペジオシン）産生で抗菌作用。発酵食品スターターとしても使用。",
    },

    "Bacillus coagulans": {
        "major_suppliers": ["Ganeden (GanedenBC30®)", "Sabinsa (LactoSpore®)", "Unique Biotech"],
        "japan_suppliers": ["太陽化学 (GanedenBC30®)", "三菱商事ライフサイエンス (LactoSpore®)"],
        "oem_forms": ["powder", "capsule", "tablet", "functional_food", "beverage"],
        "typical_grade": "Food / Probiotic",
        "certifications": ["GRAS (GRN 399)", "Non-GMO", "Kosher", "Halal"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "500 g",
        "notes": "芽胞形成菌で熱・酸・製造プロセスに強い。常温保管可能。食品添加が容易。",
    },

    "Pectinase": {
        "major_suppliers": ["Novozymes", "DSM (Rapidase®)", "AB Enzymes", "Amano Enzyme"],
        "japan_suppliers": ["天野エンザイム (Amano Enzyme)", "ノボザイムズジャパン", "DSM Japan"],
        "oem_forms": ["liquid", "powder", "granule"],
        "typical_grade": "Food",
        "certifications": ["GRAS", "Kosher", "Halal", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "果汁清澄・植物細胞壁分解に使用。最適pH・温度が製品によって異なる。",
    },

    "Glucose oxidase": {
        "major_suppliers": ["Novozymes", "AB Enzymes", "Amano Enzyme", "Shin Nihon Chemical"],
        "japan_suppliers": ["天野エンザイム", "新日本化学工業", "ノボザイムズジャパン"],
        "oem_forms": ["powder", "liquid", "granule"],
        "typical_grade": "Food",
        "certifications": ["GRAS", "Kosher", "Halal", "Non-GMO"],
        "price_tier": "medium",
        "lead_time_weeks": 4,
        "min_order_qty": "1 kg",
        "notes": "製パンでのグルテン強化・除酸素剤として使用。過酸化水素が副産物（カタラーゼ併用推奨）。",
    },
}


def get_supplier_info(atom: dict) -> Optional[dict]:
    name = atom.get("name_en", "")
    info = SUPPLIER_DATABASE.get(name)
    if not info:
        name_clean = name.split("(")[0].strip()
        info = SUPPLIER_DATABASE.get(name_clean)
    return info


def main():
    parser = argparse.ArgumentParser(description="サプライヤー・OEM 情報を Atom に付与")
    parser.add_argument("--dry-run", action="store_true", help="対象一覧のみ表示")
    parser.add_argument("--force", action="store_true", help="既に supplier_info がある Atom も上書き")
    args = parser.parse_args()

    atoms = json.loads(ATOMS_FILE.read_text(encoding="utf-8"))

    targets = [
        a for a in atoms
        if a.get("atom_type") in {"ingredient", "enzyme", "microbe"}
        and (args.force or "supplier_info" not in a)
    ]

    print(f"🏭 サプライヤーエンリッチ対象: {len(targets)} Atom")

    if args.dry_run:
        for a in targets:
            info = get_supplier_info(a)
            found = "✅" if info else "❓"
            print(f"  {found}  {a['atom_id']:35s}  {a['name_en']}")
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
        info = get_supplier_info(target)

        if info:
            atom_index[target["atom_id"]]["supplier_info"] = info
            suppliers_str = ", ".join(info["major_suppliers"][:2])
            print(f"  ✅  [{info['price_tier']:9s}]  {name[:35]:35s}  {suppliers_str}")
            hit += 1
        else:
            print(f"  ❓  [unknown  ]  {name}")
            miss += 1

    # 上書き保存
    ATOMS_FILE.write_text(
        json.dumps(list(atom_index.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ 完了  hit={hit}  miss={miss}")
    print(f"💾 保存: {ATOMS_FILE}")
    print("\n次のステップ:")
    print("  python3 scripts/enrich_patents_lens.py --dry-run")


if __name__ == "__main__":
    main()
