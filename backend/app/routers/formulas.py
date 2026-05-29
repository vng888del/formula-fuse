from __future__ import annotations
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from app.models.formula import (
    FuseRequest, AnalyzeRequest, FormulaSaveRequest,
    SafetyGateResult, AIAnalysisResult,
    SuggestRequest, SuggestResult, SuggestedAtom,
    CostEstimateRequest, CostEstimateResult,
    DoseGuideRequest, DoseGuideResult, AtomDoseGuide,
    RegulatoryCheckRequest, RegulatoryCheckResult, RegulatoryCheckItem,
)
from app.services.fuse_engine import fuse_atoms
from app.services.risk_gate import evaluate_safety_gate
from app.services.ai_router import analyze_formula
from app.services.report_generator import generate_markdown_report
from app.db.database import save_formula, get_all_formulas, get_formula_by_id

router = APIRouter(prefix="/formula", tags=["formula"])


@router.post("/fuse")
async def fuse(req: FuseRequest):
    if len(req.atom_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 atoms required")
    if len(req.atom_ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 atoms per formula")
    return fuse_atoms(req.atom_ids)


@router.post("/safety-gate")
async def safety_gate(req: FuseRequest):
    fused = fuse_atoms(req.atom_ids)
    return evaluate_safety_gate(fused.all_risk_tags, atoms=fused.atoms)


@router.post("/analyze")
async def analyze(
    req: AnalyzeRequest,
    x_ai_provider_key: Optional[str] = Header(None),
):
    if not x_ai_provider_key:
        raise HTTPException(status_code=400, detail="API key required in X-AI-Provider-Key header")
    api_key = x_ai_provider_key

    safety = evaluate_safety_gate(req.fused_formula.all_risk_tags, atoms=req.fused_formula.atoms)

    if safety.safety_status in ("Red", "Black"):
        req.fused_formula.atoms = [
            {k: v for k, v in a.items() if k not in ("supplier_keywords", "process_keywords")}
            for a in req.fused_formula.atoms
        ]

    return await analyze_formula(
        fused=req.fused_formula,
        safety=safety,
        ai_provider=req.ai_provider,
        api_key=api_key,
        model=req.model,
    )


@router.post("/save")
async def save(req: FormulaSaveRequest):
    return save_formula(req.model_dump())


@router.get("/history")
async def history():
    return get_all_formulas()


@router.get("/history/{formula_id}")
async def get_formula(formula_id: str):
    f = get_formula_by_id(formula_id)
    if not f:
        raise HTTPException(status_code=404, detail="Formula not found")
    return f


@router.get("/history/{formula_id}/report")
async def get_report(formula_id: str):
    from fastapi.responses import PlainTextResponse
    f = get_formula_by_id(formula_id)
    if not f:
        raise HTTPException(status_code=404, detail="Formula not found")

    ai_data = f.get("ai_analysis") or {}
    safety_data = f.get("safety_result") or {}
    fused_data = f.get("fused_formula") or {}

    analysis = AIAnalysisResult(**ai_data) if ai_data else AIAnalysisResult()
    safety = SafetyGateResult(**safety_data) if safety_data else SafetyGateResult(
        safety_status="Yellow", risk_tags_detected=[]
    )
    atoms = fused_data.get("atoms", [])

    md = generate_markdown_report(
        formula_name=f.get("name", "Untitled Formula"),
        atom_ids=f.get("atom_ids", []),
        atoms=atoms,
        analysis=analysis,
        safety=safety,
    )
    return PlainTextResponse(content=md, media_type="text/markdown")


@router.post("/suggest")
async def suggest(req: SuggestRequest) -> SuggestResult:
    """逆引き：目的・ゴールからAtomを提案"""
    from app.db.database import get_all_atoms, get_all_bond_rules

    goal = req.goal
    max_atoms = req.max_atoms
    atom_types = req.atom_types

    goal_lower = goal.lower()
    atoms = get_all_atoms()
    bond_rules = get_all_bond_rules()

    GOAL_KEYWORDS = {
        "睡眠": ["sleep", "melatonin", "gaba", "theanine", "anti_stress", "sleep_support", "sedative"],
        "認知": ["cognitive", "memory", "brain", "neuroprotect", "focus", "concentration"],
        "stress": ["stress", "adaptogen", "cortisol", "anxiolytic", "relaxation"],
        "スポーツ": ["sport", "performance", "muscle", "endurance", "recovery", "carnosine", "protein"],
        "腸": ["gut", "probiotic", "prebiotic", "intestinal", "microbiome", "fiber", "fermentation"],
        "免疫": ["immune", "immunity", "immunol", "antiviral", "antimicrobial"],
        "美肌": ["skin", "beauty", "collagen", "hyaluronic", "antioxidant", "uv"],
        "抗老化": ["longevity", "aging", "anti_aging", "senolytic", "mitochondr", "nad", "sirtuin"],
        "抗炎症": ["anti_inflamm", "inflammation", "cox", "lox", "cytokine"],
        "代謝": ["metabol", "insulin", "blood_sugar", "lipid", "fat", "weight"],
        "エネルギー": ["energy", "atp", "mitochondr", "fatigue", "vitality", "coq10"],
        "関節": ["joint", "cartilage", "arthritis", "collagen", "inflammation"],
    }

    def score_atom(atom):
        if atom.get("atom_type") not in (atom_types or ["ingredient"]):
            return 0, []
        
        score = 0
        reasons = []
        
        all_text = " ".join([
            atom.get("name_en", "").lower(),
            atom.get("name_ja", ""),
            atom.get("category", "").lower(),
            " ".join(atom.get("known_actions", [])).lower(),
            " ".join(atom.get("possible_bonds", [])).lower(),
            " ".join(atom.get("evidence_keywords", [])).lower(),
        ])
        
        # Direct goal text match
        if goal_lower in all_text:
            score += 30
            reasons.append(f"'{goal}'に直接マッチ")
        
        # Keyword mapping
        for jp_key, eng_keywords in GOAL_KEYWORDS.items():
            if jp_key in goal or jp_key in goal_lower:
                for kw in eng_keywords:
                    if kw in all_text:
                        score += 15
                        if not any("キーワード" in r for r in reasons):
                            reasons.append(f"目的「{jp_key}」に関連: {kw}")
                        break
        
        # English keyword match in goal
        for kw in goal_lower.split():
            if len(kw) > 3 and kw in all_text:
                score += 10
                reasons.append(f"'{kw}'にマッチ")
        
        # Evidence bonus
        pm = len(atom.get("pubmed_evidence", []))
        if pm >= 5: score += 10
        elif pm >= 3: score += 5
        elif pm >= 1: score += 2
        
        # Bond rule bonus — count rules this atom participates in
        bonds = sum(
            1 for r in bond_rules
            if r["source_atom_type"] == atom.get("atom_type") and
               any(t in " ".join(atom.get("known_actions", []) + atom.get("possible_bonds", [])) 
                   for t in r.get("source_required_tags", []))
        )
        score += min(bonds * 3, 15)
        
        return score, reasons

    scored = []
    for atom in atoms:
        s, reasons = score_atom(atom)
        if s > 0:
            supplier = atom.get("supplier_info", {})
            bond_count = sum(
                1 for r in bond_rules
                if r["source_atom_type"] == atom.get("atom_type") or
                   r["target_atom_type"] == atom.get("atom_type")
            )
            scored.append(SuggestedAtom(
                atom_id=atom["atom_id"],
                name_ja=atom["name_ja"],
                name_en=atom["name_en"],
                atom_type=atom.get("atom_type", "ingredient"),
                category=atom.get("category", ""),
                relevance_score=round(s, 1),
                match_reasons=reasons[:3],
                pubmed_count=len(atom.get("pubmed_evidence", [])),
                price_tier=supplier.get("price_tier", "unknown") if supplier else "unknown",
                bond_count=bond_count,
            ))

    scored.sort(key=lambda x: x.relevance_score, reverse=True)
    top = scored[:max_atoms]

    # Simple formula concept
    names = [a.name_ja for a in top[:3]]
    concept = f"「{goal}」サポートフォーミュラ（{' + '.join(names)}ほか）"

    return SuggestResult(goal=goal, suggested_atoms=top, formula_concept=concept)


@router.post("/cost-estimate")
async def cost_estimate(req: CostEstimateRequest) -> CostEstimateResult:
    """原価シミュレーター：選択したAtomの概算製造コスト"""
    from app.db.database import get_atom_by_id

    atom_ids = req.atom_ids
    daily_dose_g = req.daily_dose_g
    batch_size_kg = req.batch_size_kg

    TIER_COST = {
        "low":       (3, 15),
        "medium":    (15, 50),
        "high":      (50, 200),
        "very_high": (200, 800),
        "unknown":   (20, 80),
    }

    breakdown = []
    total_low = 0.0
    total_high = 0.0
    notes = []

    n = len(atom_ids) or 1
    per_atom_dose_g = daily_dose_g / n

    for aid in atom_ids:
        atom = get_atom_by_id(aid)
        if not atom:
            continue
        supplier = atom.get("supplier_info", {})
        tier = supplier.get("price_tier", "unknown") if supplier else "unknown"
        lo, hi = TIER_COST.get(tier, TIER_COST["unknown"])
        atom_cost_lo = lo * batch_size_kg
        atom_cost_hi = hi * batch_size_kg
        total_low += lo
        total_high += hi
        breakdown.append({
            "atom_id":   atom["atom_id"],
            "name_ja":   atom["name_ja"],
            "price_tier": tier,
            "cost_per_kg_range": f"¥{lo:,}–¥{hi:,}/kg",
            "batch_cost_range":  f"¥{atom_cost_lo:,.0f}–¥{atom_cost_hi:,.0f}",
        })
        if tier in ("high", "very_high"):
            notes.append(f"{atom['name_ja']} は高コスト原料（{tier}）— 配合比率の最適化を推奨")

    # Per serving estimate (assume 500mg per atom per serving)
    serving_g = per_atom_dose_g / 1000
    serve_lo = total_low * serving_g
    serve_hi = total_high * serving_g

    total_tier = "low" if total_high < 50 else "medium" if total_high < 150 else "high" if total_high < 400 else "very_high"

    notes.append(f"バッチ{batch_size_kg}kg製造、1日{daily_dose_g}g/Atom配分で試算")
    notes.append("実際の原価はサプライヤー見積・グレード・数量によって大きく変動します")

    return CostEstimateResult(
        atom_ids=atom_ids,
        daily_dose_g=daily_dose_g,
        batch_size_kg=batch_size_kg,
        cost_breakdown=breakdown,
        estimated_cost_per_kg=f"¥{total_low:,}–¥{total_high:,}/kg (原料合計)",
        estimated_cost_per_serving=f"¥{serve_lo:.1f}–¥{serve_hi:.1f}/serving",
        cost_tier=total_tier,
        notes=notes,
    )


# ── Clinical dose ranges (mg) for known supplement ingredients ────────────────
_DOSE_DB: dict[str, dict] = {
    # Vitamins & minerals
    "vitamin_c":          {"min": 500,   "max": 2000,  "suggest": 1000, "form": "アスコルビン酸粉末", "basis": "臨床試験", "notes": ["抗酸化・免疫サポートの臨床量は1000mg/日", "高用量(2g超)は下痢リスク"]},
    "vitamin_d3":         {"min": 25,    "max": 125,   "suggest": 50,   "form": "ソフトゲル/油溶液(mcg換算)", "basis": "臨床試験", "notes": ["25mcg=1000 IU", "血中25(OH)D目標は40-60 ng/mL", "脂溶性なので食後摂取推奨"]},
    "magnesium":          {"min": 200,   "max": 400,   "suggest": 300,  "form": "グリシン酸Mg/クエン酸Mg", "basis": "栄養所要量", "notes": ["グリシン酸塩は吸収率高く胃腸副作用少ない", "就寝前摂取で睡眠サポート効果"]},
    "zinc":               {"min": 10,    "max": 30,    "suggest": 15,   "form": "ビスグリシン酸Zn", "basis": "臨床試験", "notes": ["空腹時摂取で吸収率向上", "銅枯渇防止のためCu:Zn=1:10比率推奨"]},
    "iron":               {"min": 18,    "max": 45,    "suggest": 18,   "form": "フマル酸第一鉄", "basis": "栄養所要量", "notes": ["ビタミンCと同時摂取で吸収2-3倍", "カルシウム・タンニンと同時摂取避ける", "過剰摂取リスク注意"]},
    "calcium":            {"min": 500,   "max": 1000,  "suggest": 600,  "form": "クエン酸Ca/炭酸Ca", "basis": "栄養所要量", "notes": ["1回500mg以下に分割摂取で吸収率向上", "ビタミンD3との併用必須"]},
    "selenium":           {"min": 55,    "max": 200,   "suggest": 100,  "form": "セレン酵母(mcg単位)", "basis": "臨床試験", "notes": ["400mcg超で毒性リスク", "有機セレン(酵母)は無機塩より吸収率高い"]},
    "iodine":             {"min": 150,   "max": 400,   "suggest": 150,  "form": "ヨウ化カリウム(mcg単位)", "basis": "栄養所要量", "notes": ["甲状腺疾患既往者は医師相談必須", "日本人は食事から摂取過多になりやすい"]},
    "biotin":             {"min": 1000,  "max": 10000, "suggest": 2500, "form": "粉末(mcg単位)", "basis": "サプリメント一般量", "notes": ["水溶性で過剰リスク低い", "抗生物質使用時は腸内産生低下"]},
    "niacin":             {"min": 15,    "max": 35,    "suggest": 20,   "form": "ニコチン酸アミド推奨", "basis": "栄養所要量", "notes": ["ニコチン酸はフラッシュリスク(顔面紅潮)", "ニコチン酸アミドはフラッシュなし"]},
    # Amino acids
    "l_theanine":         {"min": 100,   "max": 400,   "suggest": 200,  "form": "純粉末/カプセル", "basis": "臨床試験", "notes": ["カフェインとの1:2比率(L-テアニン:カフェイン)で相乗効果", "100mgで30-40分以内に効果発現"]},
    "l_glutamine":        {"min": 5000,  "max": 20000, "suggest": 10000,"form": "粉末(大量摂取向け)", "basis": "臨床試験", "notes": ["腸管バリア修復目的は10-20g/日", "運動後リカバリーは5g/回"]},
    "l_carnitine":        {"min": 1000,  "max": 3000,  "suggest": 2000, "form": "L-カルニチン酒石酸塩", "basis": "臨床試験", "notes": ["食事(特に脂肪食)と同時摂取で効果最大化", "赤みの少ない食生活の場合は補給量増加も検討"]},
    "beta_alanine":       {"min": 2000,  "max": 6400,  "suggest": 3200, "form": "粉末", "basis": "臨床試験(ISSN推奨)", "notes": ["パレステジア(ピリピリ感)は分割摂取で軽減", "効果は4週間以上の継続で最大化", "800mg以下/回に分割推奨"]},
    "creatine":           {"min": 3000,  "max": 5000,  "suggest": 5000, "form": "クレアチン一水和物粉末", "basis": "臨床試験(ISSN推奨)", "notes": ["ローディング不要・3-5g/日で4週間で効果", "水分摂取量増加(2-3L/日)を推奨"]},
    "gaba":               {"min": 100,   "max": 750,   "suggest": 300,  "form": "粉末/カプセル", "basis": "臨床試験", "notes": ["就寝30分前摂取で睡眠潜時短縮効果", "BBB透過性は個人差あり"]},
    "5_htp":              {"min": 100,   "max": 300,   "suggest": 150,  "form": "グリフォニアシード抽出物", "basis": "臨床試験", "notes": ["SSRI/MAOIとの併用絶対禁忌", "カルビドパとの併用でセロトニン症候群リスク"]},
    "nac":                {"min": 600,   "max": 1800,  "suggest": 600,  "form": "N-アセチルシステイン粉末", "basis": "臨床試験", "notes": ["強い硫黄臭あり→カプセル化推奨", "グルタチオン前駆体として抗酸化補助"]},
    # Botanicals / Adaptogens
    "ashwagandha":        {"min": 300,   "max": 600,   "suggest": 300,  "form": "KSM-66/Sensoril標準化抽出物", "basis": "臨床試験", "notes": ["ウィサノリド5%標準化推奨", "就寝前摂取でコルチゾール抑制効果最大化"]},
    "rhodiola":           {"min": 200,   "max": 600,   "suggest": 300,  "form": "Salidroside 1%/Rosavins 3%標準化抽出物", "basis": "臨床試験", "notes": ["起床後空腹時摂取が効果的", "4週間後に2週間休薬するサイクリングを推奨"]},
    "panax_ginseng":      {"min": 200,   "max": 400,   "suggest": 200,  "form": "Ginsenoside Rb1+Rg1 標準化抽出物", "basis": "臨床試験", "notes": ["Ginsenoside 5-7%標準化品使用推奨", "高用量では不眠・興奮に注意"]},
    "cordyceps":          {"min": 1000,  "max": 3000,  "suggest": 1500, "form": "Cs-4発酵抽出物 or 子実体粉末", "basis": "臨床試験", "notes": ["コルジセピン含量で品質差大きい", "運動前60-90分前摂取で持久力効果"]},
    "bacopa":             {"min": 300,   "max": 600,   "suggest": 300,  "form": "Bacosides 20-55%標準化抽出物", "basis": "臨床試験", "notes": ["効果発現に4-12週間の継続が必要", "脂肪含む食事と同時摂取で吸収率向上"]},
    "lions_mane":         {"min": 500,   "max": 3000,  "suggest": 1000, "form": "子実体抽出物 or 菌糸体粉末", "basis": "臨床試験", "notes": ["子実体抽出物はβグルカン+エリナシン含有", "菌糸体粉末は成分プロファイルが異なる点に注意"]},
    "reishi":             {"min": 1000,  "max": 3000,  "suggest": 1500, "form": "子実体抽出物(トリテルペン+βグルカン)", "basis": "臨床試験", "notes": ["苦味強いのでカプセル化/コーティング推奨", "免疫調整効果は8-12週で最大化"]},
    # Antioxidants / Polyphenols
    "curcumin":           {"min": 500,   "max": 2000,  "suggest": 500,  "form": "Meriva/BCM-95/Theracurmin(生物活性型)", "basis": "臨床試験", "notes": ["ピペリン(5-20mg)との併用で吸収2000%向上", "通常クルクミンは吸収率が極めて低い→特殊製剤必須"]},
    "resveratrol":        {"min": 100,   "max": 500,   "suggest": 250,  "form": "ポリゴヌム・クスピダツム抽出物", "basis": "臨床試験", "notes": ["微粉砕・リポソーム製剤で吸収率向上", "脂肪食と同時摂取推奨", "半減期短いため1日2回分割"]},
    "quercetin":          {"min": 500,   "max": 1000,  "suggest": 500,  "form": "Quercefit(リン脂質複合体)", "basis": "臨床試験", "notes": ["Quercefitは通常クエルセチンより吸収20倍", "ブロメラインとの併用で抗炎症効果増強"]},
    "egcg":               {"min": 200,   "max": 800,   "suggest": 400,  "form": "緑茶抽出物(カテキン50-90%標準化)", "basis": "臨床試験", "notes": ["空腹時摂取で吸収率3倍↑（ただし胃刺激注意）", "EGCG 800mg超/日で肝臓負担リスク"]},
    "coq10":              {"min": 100,   "max": 300,   "suggest": 200,  "form": "ユビキノール(還元型)推奨", "basis": "臨床試験", "notes": ["ユビキノールはQ10の還元型で吸収2-8倍", "脂肪食と同時摂取必須"]},
    "alpha_lipoic_acid":  {"min": 300,   "max": 600,   "suggest": 300,  "form": "R-ALA(R型)推奨", "basis": "臨床試験", "notes": ["R型は生物活性がS型の2倍", "空腹時摂取で吸収率向上", "ビオチン欠乏を引き起こす可能性→ビオチン併用検討"]},
    "glutathione":        {"min": 250,   "max": 1000,  "suggest": 500,  "form": "リポソーム型/アセチル化型推奨", "basis": "臨床試験", "notes": ["通常グルタチオンは経口吸収が非常に低い", "リポソーム型/アセチルグルタチオンで吸収率改善"]},
    "fisetin":            {"min": 100,   "max": 500,   "suggest": 200,  "form": "固体分散体/リポソーム型", "basis": "前臨床/初期臨床", "notes": ["脂溶性→脂肪食と同時摂取必須", "セノリティクス用途では高用量(20mg/kg)が検討されている", "長期安全性データは限定的"]},
    "urolithin_a":        {"min": 500,   "max": 2000,  "suggest": 1000, "form": "合成ウロリチンA (Mitopure)", "basis": "臨床試験(Mitopure)", "notes": ["腸内細菌によるエラジタンニン変換には個人差あり", "合成型(Mitopure)は再現性の高い摂取が可能"]},
    "sulforaphane":       {"min": 30,    "max": 100,   "suggest": 50,   "form": "ブロッコリーシード抽出物(ミロシナーゼ活性型)", "basis": "臨床試験", "notes": ["ミロシナーゼ活性化型が必須", "スプラウト粉末はミロシナーゼ失活に注意", "Nrf2経路を活性化"]},
    # Omega fatty acids
    "omega3_dha":         {"min": 1000,  "max": 3000,  "suggest": 2000, "form": "rTG型 or PL型EPA+DHA", "basis": "臨床試験(AHA推奨)", "notes": ["EPA:DHA比率は用途で変える(抗炎症→EPA多め、脳→DHA多め)", "酸化防止のためビタミンE添加推奨", "抗凝固薬との相互作用注意"]},
    # Sleep
    "melatonin":          {"min": 0.5,   "max": 5,     "suggest": 1,    "form": "即放/徐放カプセル", "basis": "臨床試験", "notes": ["低用量(0.5-1mg)が生理的で時差ぼけ・睡眠位相調整に有効", "就寝30-60分前摂取", "高用量は翌朝の眠気リスク"]},
    # Longevity
    "nmn":                {"min": 250,   "max": 1000,  "suggest": 500,  "form": "粉末/舌下溶解タブレット", "basis": "初期臨床試験", "notes": ["舌下摂取でバイオアベイラビリティ向上の報告あり", "ナイアシン(NR/NMN)は腸内細菌叢への影響を考慮", "レスベラトロールとの相乗効果が示唆される"]},
    "resveratrol_nmn":    {"min": 250,   "max": 500,   "suggest": 250,  "form": "マイクロカプセル", "basis": "初期臨床試験", "notes": ["NMNとの相乗効果を期待する場合はSIRT1経路を意識した用量設計"]},
    # Gut health
    "lactobacillus":      {"min": 1e9,   "max": 1e10,  "suggest": 5e9,  "form": "耐酸性カプセル(10億CFU単位)", "basis": "臨床試験", "notes": ["食後摂取で生存率向上", "保管は冷蔵(4℃)推奨", "抗生物質と同時摂取は2-4時間あける"]},
    "bifidobacterium":    {"min": 1e9,   "max": 1e10,  "suggest": 5e9,  "form": "耐酸性カプセル(10億CFU単位)", "basis": "臨床試験", "notes": ["食後摂取で生存率向上", "フルクトオリゴ糖(FOS)との併用でプレバイオティクス相乗効果"]},
    "inulin":             {"min": 5000,  "max": 15000, "suggest": 8000, "form": "粉末(水溶性)", "basis": "臨床試験", "notes": ["急激な増量でガス・腸不快感→段階的に増量", "ビフィズス菌・乳酸菌のプレバイオティクス基質"]},
    "fos":                {"min": 3000,  "max": 10000, "suggest": 5000, "form": "粉末", "basis": "臨床試験", "notes": ["5g超でガス産生増加", "腸内pH低下により短鎖脂肪酸産生促進"]},
    # Joint / beauty
    "collagen":           {"min": 5000,  "max": 15000, "suggest": 10000,"form": "加水分解コラーゲンペプチド", "basis": "臨床試験", "notes": ["ビタミンCとの同時摂取でコラーゲン合成促進", "Type I(皮膚・腱)とType II(関節)で分けて設計"]},
    "hyaluronic_acid":    {"min": 80,    "max": 200,   "suggest": 120,  "form": "低分子ヒアルロン酸(5kDa以下)推奨", "basis": "臨床試験", "notes": ["低分子は腸管吸収率高い", "食事と同時摂取推奨"]},
    "boswellia":          {"min": 300,   "max": 1200,  "suggest": 500,  "form": "AKBA 30%以上標準化抽出物(Aflapin/5-Loxin)", "basis": "臨床試験", "notes": ["AKBA含量30%以上の標準化品選択", "脂肪食と同時摂取で吸収率向上", "4週間以上で膝関節スコア改善"]},
    # Anti-inflammatory
    "berberine":          {"min": 500,   "max": 1500,  "suggest": 500,  "form": "塩酸ベルベリン", "basis": "臨床試験", "notes": ["1日3回分割摂取(食直前)で血糖コントロール", "CYP3A4代謝薬との相互作用注意", "妊婦禁忌"]},
    "piperine":           {"min": 5,     "max": 20,    "suggest": 10,   "form": "BioPerine(95%ピペリン標準化)", "basis": "臨床試験", "notes": ["クルクミン・ビタミンC・CoQ10の吸収を2000-20倍増強", "CYP3A4/P-gpへの影響で薬物相互作用注意", "他の成分と同時摂取必須"]},
    # Cognitive
    "phosphatidylserine": {"min": 100,   "max": 300,   "suggest": 300,  "form": "大豆由来PS(GRAS)", "basis": "臨床試験", "notes": ["食事と同時摂取で吸収率向上", "認知機能改善のFDA Qualified Health Claim取得済み"]},
    "alpha_gpc":          {"min": 300,   "max": 1200,  "suggest": 600,  "form": "アルファGPC粉末(50%含量換算)", "basis": "臨床試験", "notes": ["コリン供給源として最も吸収率高い形態", "コリン過剰でTMAO産生→ブロメラインで軽減"]},
    # Energy / Performance
    "caffeine":           {"min": 100,   "max": 400,   "suggest": 200,  "form": "無水カフェイン", "basis": "臨床試験(ISSN)", "notes": ["運動30-60分前摂取で持久・認知パフォーマンス向上", "3-6mg/kg体重が有効量", "習慣化で耐性形成→休薬サイクル推奨"]},
    # Skin / antioxidant
    "astaxanthin":        {"min": 4,     "max": 12,    "suggest": 6,    "form": "ヘマトコッカス藻抽出物(5-10%含量品)", "basis": "臨床試験", "notes": ["脂溶性→脂肪食と同時摂取必須", "光・熱・酸素に不安定→遮光充填剤使用推奨"]},
    "lutein":             {"min": 10,    "max": 20,    "suggest": 10,   "form": "万寿菊抽出物(20%含量品)", "basis": "臨床試験(AREDS2)", "notes": ["ゼアキサンチン2mgとの同時摂取(AREDS2処方)", "脂肪食と同時摂取で吸収率向上"]},
}

def _get_dose_for_atom(atom: dict) -> dict:
    aid = atom.get("atom_id", "")
    name_en = atom.get("name_en", "").lower().replace(" ", "_").replace("-", "_")
    for key in [aid, name_en]:
        if key in _DOSE_DB:
            return _DOSE_DB[key]
        for db_key in _DOSE_DB:
            if db_key in key or key in db_key:
                return _DOSE_DB[db_key]
    atom_type = atom.get("atom_type", "ingredient")
    if atom_type == "microbe":
        return {"min": 1e9, "max": 1e10, "suggest": 5e9, "form": "耐酸性カプセル(CFU単位)", "basis": "一般的プロバイオティクス量", "notes": ["菌種・株に応じた投与量設定が推奨"]}
    if atom_type == "enzyme":
        return {"min": 100, "max": 500, "suggest": 200, "form": "腸溶カプセル", "basis": "一般的酵素量", "notes": ["活性単位(IU/GDU等)での規格管理推奨"]}
    return {"min": 50, "max": 500, "suggest": 200, "form": "カプセル/錠剤", "basis": "推定(文献なし)", "notes": ["臨床データが限定的のため専門家へ相談推奨"]}


@router.post("/dose-guide")
async def dose_guide(req: DoseGuideRequest) -> DoseGuideResult:
    """配合比率ガイド：各Atomの臨床推奨投与量を返す"""
    from app.db.database import get_atom_by_id

    guides = []
    total_mg = 0.0

    for aid in req.atom_ids:
        atom = get_atom_by_id(aid)
        if not atom:
            continue
        d = _get_dose_for_atom(atom)
        suggest = d["suggest"]
        total_mg += suggest
        guides.append(AtomDoseGuide(
            atom_id=atom["atom_id"],
            name_ja=atom["name_ja"],
            name_en=atom["name_en"],
            suggested_dose_mg=suggest,
            dose_range_min_mg=d["min"],
            dose_range_max_mg=d["max"],
            dose_basis=d["basis"],
            typical_form=d["form"],
            key_notes=d.get("notes", []),
        ))

    serving_g = total_mg / 1000
    serving_summary = f"推奨総量: {total_mg:.0f}mg ({serving_g:.1f}g) / 日"

    notes = []
    if total_mg > 10000:
        notes.append(f"総配合量が{serving_g:.1f}gと多め — 複数回分割摂取（朝/昼/夜）を推奨")
    if total_mg > 20000:
        notes.append("20g超のサービングは製剤上の課題あり — カプセル数・剤形を要検討")
    notes.append("上記は臨床文献に基づく参考値です。実際の配合は管理栄養士・薬剤師と確認してください")

    return DoseGuideResult(
        atom_ids=req.atom_ids,
        total_daily_mg=total_mg,
        atom_guides=guides,
        serving_summary=serving_summary,
        formulation_notes=notes,
    )


# ── Regulatory checklist ──────────────────────────────────────────────────────

@router.post("/regulatory-check")
async def regulatory_check(req: RegulatoryCheckRequest) -> RegulatoryCheckResult:
    """規制チェックリスト：選択Atomの規制上の課題を一覧化"""
    from app.db.database import get_atom_by_id

    checklist: list[RegulatoryCheckItem] = []
    required_actions: list[str] = []
    expert_reviews: list[str] = []
    overall_flags = []

    for aid in req.atom_ids:
        atom = get_atom_by_id(aid)
        if not atom:
            continue

        name = atom.get("name_ja", aid)
        gras = atom.get("gras", {}) or {}
        risk_tags = atom.get("risk_tags", [])
        atom_type = atom.get("atom_type", "ingredient")
        supplier = atom.get("supplier_info", {}) or {}
        reg_notes = atom.get("regulatory_notes", [])

        gras_status = gras.get("status", "unknown")
        jp_status = gras.get("jp_status", "")

        # GRAS / FDA status
        if gras_status == "GRAS":
            checklist.append(RegulatoryCheckItem(
                category="FDA (USA)", item=f"{name} — GRAS認定",
                status="pass", detail=gras.get("basis", "Generally Recognized as Safe"),
            ))
        elif gras_status == "NDI":
            checklist.append(RegulatoryCheckItem(
                category="FDA (USA)", item=f"{name} — NDI届出必要",
                status="warn", detail="New Dietary Ingredient — FDA事前届出が必要",
            ))
            required_actions.append(f"{name}: FDA NDI届出書類の準備")
        elif gras_status == "food_additive":
            checklist.append(RegulatoryCheckItem(
                category="FDA (USA)", item=f"{name} — 食品添加物申請",
                status="warn", detail="食品添加物として使用するにはFDA Food Additive Petition必要",
            ))
            required_actions.append(f"{name}: FDA Food Additive Petition検討")
        else:
            checklist.append(RegulatoryCheckItem(
                category="FDA (USA)", item=f"{name} — 規制状況不明",
                status="info", detail="GRASデータ未取得 — 使用前に確認が必要",
            ))

        # Japan status
        if jp_status:
            if "食品" in jp_status or "FOSHU" in jp_status or "機能性表示" in jp_status:
                checklist.append(RegulatoryCheckItem(
                    category="日本 (JP)", item=f"{name} — {jp_status}",
                    status="pass", detail="日本の食品制度内での使用実績あり",
                ))
            elif "医薬" in jp_status or "成分" in jp_status:
                checklist.append(RegulatoryCheckItem(
                    category="日本 (JP)", item=f"{name} — 医薬品的成分",
                    status="fail", detail=jp_status + " — 食品への配合に制限あり",
                ))
                required_actions.append(f"{name}: 厚生労働省への事前確認・専門家相談必須")
                overall_flags.append("red")
            else:
                checklist.append(RegulatoryCheckItem(
                    category="日本 (JP)", item=f"{name} — JP状況: {jp_status}",
                    status="warn", detail="詳細確認が推奨されます",
                ))
        else:
            if atom_type == "ingredient":
                checklist.append(RegulatoryCheckItem(
                    category="日本 (JP)", item=f"{name} — JP状況未確認",
                    status="info", detail="厚生労働省・消費者庁の使用可否リストを照合してください",
                ))

        # Risk tag checks
        for tag in risk_tags:
            if tag in ("drug_interaction_high", "contraindicated_pregnancy", "hepatotoxic_potential", "liver_toxicity_high_dose"):
                checklist.append(RegulatoryCheckItem(
                    category="安全性", item=f"{name} — 高リスクタグ: {tag}",
                    status="fail", detail="重篤な副作用・相互作用リスク — 警告表示・専門家監修が必須",
                ))
                expert_reviews.append(f"{name} ({tag}): 薬剤師・医師による安全性審査")
                overall_flags.append("red")
            elif tag in ("pregnancy_caution", "drug_interaction_moderate", "blood_thinner_interaction",
                         "blood_sugar_caution", "thyroid_caution", "autoimmune_caution"):
                checklist.append(RegulatoryCheckItem(
                    category="安全性", item=f"{name} — 注意タグ: {tag}",
                    status="warn", detail="特定条件下での注意喚起が必要 — ラベル表示を検討",
                ))
                overall_flags.append("yellow")

        # Regulatory notes from atom data
        for note in reg_notes[:2]:
            checklist.append(RegulatoryCheckItem(
                category="規制メモ", item=f"{name}",
                status="info", detail=note,
            ))

        # Microbe / enzyme special checks
        if atom_type == "microbe":
            checklist.append(RegulatoryCheckItem(
                category="プロバイオティクス", item=f"{name} — 菌株同定書類",
                status="warn", detail="菌株レベルの同定(16S rRNA解析等)と安全性確認書類が必要",
            ))
            required_actions.append(f"{name}: 菌株同定書類・安全性データシートの準備")
        if atom_type == "enzyme":
            checklist.append(RegulatoryCheckItem(
                category="酵素", item=f"{name} — 酵素活性規格",
                status="warn", detail="活性単位(IU/GDU等)での品質規格設定が必要",
            ))

        # Supplier certifications
        certs = supplier.get("certifications", [])
        if certs:
            checklist.append(RegulatoryCheckItem(
                category="品質認証", item=f"{name} — {', '.join(certs[:3])}",
                status="pass", detail="主要サプライヤーが取得済みの認証",
            ))
        else:
            checklist.append(RegulatoryCheckItem(
                category="品質認証", item=f"{name} — 認証情報未確認",
                status="info", detail="ISO/GMP/HACCP認証サプライヤーの選定を推奨",
            ))

    # Market-level checks
    if req.target_market in ("JP", "ALL"):
        checklist.append(RegulatoryCheckItem(
            category="日本 — 表示", item="機能性表示食品制度",
            status="info", detail="機能性表示を行う場合は消費者庁への届出が必要(届出型)またはSRレビューが必要",
        ))
        checklist.append(RegulatoryCheckItem(
            category="日本 — 製造", item="GMP認定工場",
            status="warn", detail="健康食品GMPの認定工場(日健栄協/NSF等)での製造を強く推奨",
        ))
        required_actions.append("GMP認定工場での製造体制の確認")

    if req.target_market in ("US", "ALL"):
        checklist.append(RegulatoryCheckItem(
            category="FDA — 製造", item="21 CFR Part 111 (cGMP)",
            status="warn", detail="ダイエタリーサプリメントの製造はcGMP準拠が義務",
        ))

    if "red" in overall_flags:
        overall_status = "要専門家確認"
    elif "yellow" in overall_flags:
        overall_status = "注意事項あり"
    else:
        overall_status = "概ね問題なし"

    expert_reviews = list(set(expert_reviews))
    return RegulatoryCheckResult(
        atom_ids=req.atom_ids,
        target_market=req.target_market,
        overall_status=overall_status,
        checklist=checklist,
        required_actions=required_actions,
        expert_reviews=expert_reviews,
    )
