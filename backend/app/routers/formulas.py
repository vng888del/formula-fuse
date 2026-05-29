from __future__ import annotations
import os
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from app.models.formula import (
    FuseRequest, AnalyzeRequest, FormulaSaveRequest,
    SafetyGateResult, AIAnalysisResult
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


def _resolve_api_key(provider: str, byok: Optional[str]) -> str:
    if byok:
        return byok
    env_map = {
        "openai":  os.getenv("OPENAI_API_KEY", ""),
        "claude":  os.getenv("ANTHROPIC_API_KEY", ""),
        "gemini":  os.getenv("GOOGLE_API_KEY", ""),
    }
    key = env_map.get(provider, "")
    if not key:
        raise HTTPException(status_code=400, detail="API key required in X-AI-Provider-Key header")
    return key


@router.post("/analyze")
async def analyze(
    req: AnalyzeRequest,
    x_ai_provider_key: Optional[str] = Header(None),
):
    api_key = _resolve_api_key(req.ai_provider, x_ai_provider_key)

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
