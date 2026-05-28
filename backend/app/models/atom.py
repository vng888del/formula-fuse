from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class AtomType(str, Enum):
    ingredient = "ingredient"
    microbe = "microbe"
    enzyme = "enzyme"
    condition = "condition"
    goal = "goal"
    process = "process"


class Atom(BaseModel):
    atom_id: str
    name_ja: str
    name_en: str
    atom_type: AtomType
    category: str
    domain: str = "food_bio"
    known_actions: list[str] = []
    possible_bonds: list[str] = []
    risk_tags: list[str] = []
    evidence_keywords: list[str] = []
    regulatory_notes: list[str] = []
    process_keywords: list[str] = []
    supplier_keywords: list[str] = []


class AtomCreate(Atom):
    pass


class AtomInDB(Atom):
    id: Optional[str] = None
