from __future__ import annotations
from typing import Optional
from app.models.formula import SafetyStatus, SafetyGateResult

BLACK_TAGS = set()

RED_TAGS = {
    "toxicology_review_required",
    "pharmaceutical_borderline",
    "manufacturing_safety_review",
}

YELLOW_TAGS = {
    "wheat_allergen",
    "milk_allergen",
    "soy_allergen",
    "egg_allergen",
    "nut_allergen",
    "fish_allergen",
    "shellfish_allergen",
    "peanut_allergen",
    "sesame_allergen",
    "gluten_related",
    "celiac_claim_risk",
    "medical_claim_risk",
    "dose_review_required",
    "pregnancy_caution",
    "child_caution",
    "high_caffeine",
    "food_additive_review",
    "fermentation_contamination_risk",
    "microbial_safety_review",
    "claim_requires_evidence",
    "insufficient_evidence",
    "expert_review_required",
    "drug_interaction_risk",
}

ALL_ACTIONS = [
    "experiment_plan",
    "prior_art_search",
    "expert_review",
    "ingredient_sourcing",
    "process_direction",
    "productize",
    "patent_brief",
    "supplier_oem",
    "report",
]

RED_BLOCKED_ACTIONS = [
    "ingredient_sourcing",
    "process_direction",
    "productize",
    "supplier_oem",
]

# EC 番号で食品安全が確立されている酵素クラス
FOOD_SAFE_EC_PREFIXES = {
    "3.2.1",  # glycoside hydrolases (amylase, lactase, cellulase)
    "3.1.1",  # ester hydrolases (lipase)
    "3.1.3",  # phosphoric monoester hydrolases (phytase)
    "3.5.1",  # acting on C-N bonds (asparaginase)
    "2.3.2",  # acyltransferases (transglutaminase)
}

# 分子量 (g/mol) のしきい値: 以上は高分子 → 生物製剤レビュー推奨
HIGH_MW_THRESHOLD = 1500


def _assess_evidence_level(atoms: list[dict]) -> str:
    """
    PubMed エビデンス数・品質から E0–E5 を推定する。
    E0: なし, E1: 1–2件, E2: 3–5件, E3: 5–10件, E4: 10+件, E5: ヒト RCT あり
    """
    total_papers = 0
    has_rct_journal = False
    rct_journals = {"N Engl J Med", "Lancet", "JAMA", "BMJ", "Ann Intern Med",
                    "Nutrients", "Am J Clin Nutr", "J Nutr"}

    for atom in atoms:
        papers = atom.get("pubmed_evidence", [])
        total_papers += len(papers)
        for p in papers:
            if any(j in p.get("journal", "") for j in rct_journals):
                has_rct_journal = True

    if total_papers == 0:
        return "E0"
    if has_rct_journal and total_papers >= 10:
        return "E5"
    if total_papers >= 10:
        return "E4"
    if total_papers >= 5:
        return "E3"
    if total_papers >= 3:
        return "E2"
    return "E1"


def _assess_gras_notes(atoms: list[dict]) -> list[str]:
    """各 Atom の GRAS ステータスから注意事項を抽出する。"""
    notes = []
    for atom in atoms:
        gras = atom.get("gras", {})
        status = gras.get("status", "")
        name = atom.get("name_en", atom.get("atom_id", ""))

        if status == "NDI":
            notes.append(f"{name}: NDI 届出のみ（米国では dietary supplement 用途に限定）")
        elif status == "food_additive":
            notes.append(f"{name}: 食品添加物として規制（用途・使用量の制限あり）")
        elif status == "unknown":
            notes.append(f"{name}: FDA GRAS ステータス未確認 — 個別調査を推奨")
    return notes


def _assess_compound_flags(atoms: list[dict]) -> list[str]:
    """分子量・化合物データから追加リスクフラグを生成する。"""
    flags = []
    for atom in atoms:
        compound = atom.get("compound", {})
        mw = compound.get("molecular_weight")
        name = atom.get("name_en", atom.get("atom_id", ""))
        if mw and float(mw) > HIGH_MW_THRESHOLD:
            flags.append(f"{name}: 高分子量 ({mw} g/mol) — 生物製剤レビュー推奨")
    return flags


def _assess_enzyme_flags(atoms: list[dict]) -> list[str]:
    """EC 番号から酵素安全性を評価する。"""
    flags = []
    for atom in atoms:
        if atom.get("atom_type") != "enzyme":
            continue
        uniprot = atom.get("uniprot", {})
        ec_numbers = uniprot.get("ec_numbers", [])
        name = atom.get("name_en", atom.get("atom_id", ""))

        if not ec_numbers:
            continue

        all_food_safe = all(
            any(ec.startswith(prefix) for prefix in FOOD_SAFE_EC_PREFIXES)
            for ec in ec_numbers
        )
        if not all_food_safe:
            flags.append(f"{name}: EC {ec_numbers} — 食品用途での安全確認が必要")

    return flags


def _build_atom_safety_notes(atoms: list[dict]) -> list[dict]:
    """Atom ごとの安全情報サマリーを生成する。"""
    notes = []
    for atom in atoms:
        atom_id = atom.get("atom_id", "")
        name = atom.get("name_en", "")
        gras = atom.get("gras", {})
        uniprot = atom.get("uniprot", {})
        compound = atom.get("compound", {})
        evidence_count = len(atom.get("pubmed_evidence", []))

        note = {
            "atom_id":       atom_id,
            "name":          name,
            "gras_status":   gras.get("status", "unknown"),
            "jp_status":     gras.get("jp_status", "不明"),
            "evidence_count": evidence_count,
        }

        if uniprot.get("ec_numbers"):
            note["ec_numbers"] = uniprot["ec_numbers"]

        if compound.get("molecular_weight"):
            note["molecular_weight"] = compound["molecular_weight"]

        if gras.get("notes"):
            note["safety_note"] = gras["notes"]

        notes.append(note)

    return notes


def evaluate_safety_gate(
    risk_tags: list[str],
    atoms: Optional[list[dict]] = None,
) -> SafetyGateResult:
    """
    Safety Gate を評価する。

    atoms を渡すと Phase 3 の拡張評価が有効になる:
    - GRAS ステータス分析
    - PubMed エビデンスレベル推定
    - 分子量・EC番号チェック
    """
    tag_set = set(risk_tags)
    detected = list(tag_set)

    # ── Phase 3 拡張評価 ──────────────────────────────────────────────────────
    evidence_level = "E0"
    gras_notes: list[str] = []
    atom_safety_notes: list[dict] = []
    extra_warnings: list[str] = []

    if atoms:
        evidence_level = _assess_evidence_level(atoms)
        gras_notes = _assess_gras_notes(atoms)
        atom_safety_notes = _build_atom_safety_notes(atoms)
        extra_warnings += _assess_compound_flags(atoms)
        extra_warnings += _assess_enzyme_flags(atoms)

        # GRAS 未確認 Atom が複数 → 追加の要専門家確認タグを合成
        unknown_gras = [n for n in gras_notes if "未確認" in n]
        if len(unknown_gras) >= 2:
            tag_set.add("expert_review_required")
            detected = list(tag_set)

    # ── Black 判定 ────────────────────────────────────────────────────────────
    black_hits = tag_set & BLACK_TAGS
    if black_hits:
        return SafetyGateResult(
            safety_status=SafetyStatus.black,
            blocking_reasons=[f"Blocked: {', '.join(black_hits)}"],
            risk_tags_detected=detected,
            allowed_actions=[],
            restricted_actions=ALL_ACTIONS,
            required_expert_reviews=[],
            safe_alternative_direction=["安全な代替方向を検討してください。"],
            evidence_level=evidence_level,
            gras_notes=gras_notes,
            atom_safety_notes=atom_safety_notes,
        )

    # ── Red 判定 ──────────────────────────────────────────────────────────────
    red_hits = tag_set & RED_TAGS
    ferment_risk = (
        "fermentation_contamination_risk" in tag_set
        and "microbial_safety_review" in tag_set
    )
    if red_hits or ferment_risk:
        all_red = red_hits | (
            {"fermentation_contamination_risk", "microbial_safety_review"}
            if ferment_risk else set()
        )
        blocking = [f"要専門家確認: {', '.join(all_red)}"]
        blocking += extra_warnings
        allowed = [a for a in ALL_ACTIONS if a not in RED_BLOCKED_ACTIONS]
        experts = ["食品安全専門家", "規制専門家", "薬剤師"]
        return SafetyGateResult(
            safety_status=SafetyStatus.red,
            blocking_reasons=blocking,
            risk_tags_detected=detected,
            allowed_actions=allowed,
            restricted_actions=RED_BLOCKED_ACTIONS,
            required_expert_reviews=experts,
            safe_alternative_direction=[],
            evidence_level=evidence_level,
            gras_notes=gras_notes,
            atom_safety_notes=atom_safety_notes,
        )

    # ── Yellow 判定 ───────────────────────────────────────────────────────────
    yellow_hits = tag_set & YELLOW_TAGS
    if yellow_hits or extra_warnings:
        expert_notes = ["専門家確認を推奨します"] if yellow_hits else []
        return SafetyGateResult(
            safety_status=SafetyStatus.yellow,
            blocking_reasons=extra_warnings,
            risk_tags_detected=detected,
            allowed_actions=ALL_ACTIONS,
            restricted_actions=[],
            required_expert_reviews=expert_notes,
            safe_alternative_direction=[],
            evidence_level=evidence_level,
            gras_notes=gras_notes,
            atom_safety_notes=atom_safety_notes,
        )

    # ── Green 判定 ────────────────────────────────────────────────────────────
    return SafetyGateResult(
        safety_status=SafetyStatus.green,
        blocking_reasons=[],
        risk_tags_detected=detected,
        allowed_actions=ALL_ACTIONS,
        restricted_actions=[],
        required_expert_reviews=[],
        safe_alternative_direction=[],
        evidence_level=evidence_level,
        gras_notes=gras_notes,
        atom_safety_notes=atom_safety_notes,
    )
