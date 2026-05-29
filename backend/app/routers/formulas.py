from __future__ import annotations
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from app.models.formula import (
    FuseRequest, AnalyzeRequest, FormulaSaveRequest,
    SafetyGateResult, AIAnalysisResult,
    SuggestRequest, SuggestResult, SuggestedAtom,
    CostEstimateRequest, CostEstimateResult,
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
