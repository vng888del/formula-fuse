from __future__ import annotations
from app.db.database import get_atom_by_id, get_all_bond_rules
from app.models.formula import FusedFormula


def fuse_atoms(atom_ids: list[str]) -> FusedFormula:
    atoms = []
    for aid in atom_ids:
        atom = get_atom_by_id(aid)
        if atom:
            atoms.append(atom)

    all_risk_tags: list[str] = []
    all_possible_bonds: list[str] = []
    for atom in atoms:
        all_risk_tags.extend(atom.get("risk_tags", []))
        all_possible_bonds.extend(atom.get("possible_bonds", []))

    all_risk_tags = list(set(all_risk_tags))
    all_possible_bonds = list(set(all_possible_bonds))

    bond_matches = _evaluate_bond_rules(atoms)

    return FusedFormula(
        atom_ids=atom_ids,
        atoms=atoms,
        all_risk_tags=all_risk_tags,
        all_possible_bonds=all_possible_bonds,
        bond_matches=bond_matches,
    )


def _evaluate_bond_rules(atoms: list[dict]) -> list[dict]:
    rules = get_all_bond_rules()
    matches = []

    for rule in rules:
        sources = [a for a in atoms if a["atom_type"] == rule["source_atom_type"]]
        targets = [a for a in atoms if a["atom_type"] == rule["target_atom_type"]]

        for src in sources:
            for tgt in targets:
                if src["atom_id"] == tgt["atom_id"]:
                    continue
                src_ok = _tags_match(src.get("possible_bonds", []), rule.get("source_required_tags", []))
                tgt_ok = _tags_match(tgt.get("possible_bonds", []) + tgt.get("known_actions", []), rule.get("target_required_tags", []))
                if src_ok and tgt_ok:
                    matches.append({
                        "bond_rule_id": rule["bond_rule_id"],
                        "bond_type": rule["bond_type"],
                        "source_atom": src["atom_id"],
                        "target_atom": tgt["atom_id"],
                        "expected_result": rule["expected_result"],
                        "confidence": rule["confidence"],
                        "risk_level": rule["risk_level"],
                        "explanation": rule["explanation"],
                    })

    return matches


def _tags_match(atom_tags: list[str], required_tags: list[str]) -> bool:
    if not required_tags:
        return True
    for req in required_tags:
        for tag in atom_tags:
            if req == tag or req in tag or tag in req:
                return True
    return False
