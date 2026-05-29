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


class SuggestRequest(BaseModel):
    goal: str
    max_atoms: int = 6
    atom_types: Optional[List[str]] = None  # filter by type


class SuggestedAtom(BaseModel):
    atom_id: str
    name_ja: str
    name_en: str
    atom_type: str
    category: str
    relevance_score: float
    match_reasons: list[str]
    pubmed_count: int
    price_tier: str
    bond_count: int


class SuggestResult(BaseModel):
    goal: str
    suggested_atoms: list[SuggestedAtom]
    formula_concept: str


class CostEstimateRequest(BaseModel):
    atom_ids: list[str]
    daily_dose_g: float = 1.0
    batch_size_kg: float = 10.0


class CostEstimateResult(BaseModel):
    atom_ids: list[str]
    daily_dose_g: float
    batch_size_kg: float
    cost_breakdown: list[dict]
    estimated_cost_per_kg: str
    estimated_cost_per_serving: str
    cost_tier: str
    notes: list[str]
