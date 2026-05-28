from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class SafetyStatus(str, Enum):
    green = "Green"
    yellow = "Yellow"
    red = "Red"
    black = "Black"


class EvidenceLevel(str, Enum):
    e0 = "E0"
    e1 = "E1"
    e2 = "E2"
    e3 = "E3"
    e4 = "E4"
    e5 = "E5"


class BondInterpretation(BaseModel):
    bond_type: str
    atoms: list[str]
    explanation: str


class AIAnalysisResult(BaseModel):
    formula_name: str = ""
    formula_summary: str = ""
    expected_function: str = ""
    mechanism_hypothesis: str = ""
    bond_interpretation: list[BondInterpretation] = []
    safety_status: SafetyStatus = SafetyStatus.yellow
    risk_notes: list[str] = []
    evidence_level: EvidenceLevel = EvidenceLevel.e0
    evidence_needed: list[str] = []
    experiment_suggestions: list[str] = []
    ip_potential: str = ""
    product_direction: list[str] = []
    process_direction: list[str] = []
    supplier_requirements: list[str] = []
    regulatory_cautions: list[str] = []
    next_actions: list[str] = []


class SafetyGateResult(BaseModel):
    safety_status: SafetyStatus
    blocking_reasons: list[str] = []
    risk_tags_detected: list[str] = []
    allowed_actions: list[str] = []
    restricted_actions: list[str] = []
    required_expert_reviews: list[str] = []
    safe_alternative_direction: list[str] = []
    # Phase 3 additions — evidence-aware fields
    evidence_level: str = "E0"
    gras_notes: list[str] = []
    atom_safety_notes: list[dict] = []


class FuseRequest(BaseModel):
    atom_ids: list[str]


class FusedFormula(BaseModel):
    atom_ids: list[str]
    atoms: list[dict]
    all_risk_tags: list[str]
    all_possible_bonds: list[str]
    bond_matches: list[dict]


class AnalyzeRequest(BaseModel):
    fused_formula: FusedFormula
    ai_provider: str = "openai"
    model: Optional[str] = None


class FormulaSaveRequest(BaseModel):
    name: str
    atom_ids: list[str]
    fused_formula: Optional[dict] = None
    ai_analysis: Optional[dict] = None
    safety_result: Optional[dict] = None


class FormulaSaved(BaseModel):
    id: str
    name: str
    atom_ids: list[str]
    fused_formula: Optional[dict] = None
    ai_analysis: Optional[dict] = None
    safety_result: Optional[dict] = None
    created_at: Optional[str] = None
