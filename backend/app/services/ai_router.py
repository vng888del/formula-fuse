from __future__ import annotations
import json
import re
from typing import Optional
from app.models.formula import FusedFormula, AIAnalysisResult, SafetyGateResult

FORMULA_ANALYSIS_PROMPT = """あなたはFormula Intelligence Engineの解析AIです。

ユーザーが選択したAtomの組み合わせを、食品・健康食品・発酵・バイオ・素材開発の観点から解析してください。

ただし、あなたは医師・弁護士・規制当局ではありません。
安全性・特許性・法規制について確定してはいけません。
必ず「可能性がある」「検討ポイント」「専門家確認が必要」という形式で回答してください。

以下の入力JSONを解析してください。各Atomには以下の情報が含まれます：
- compound: PubChemの分子式・分子量・SMILES（化合物の場合）
- uniprot: EC番号・機能コメント・触媒反応（酵素の場合）
- gras_status: FDA GRAS認証状況と日本での法的位置づけ
- pubmed_evidence_count: PubMed掲載論文数（エビデンス強度の目安）
- top_papers: 関連論文トップ2（タイトル・掲載誌・年）
- supplier_tier: 調達コスト目安 (low/medium/high/very_high)
- oem_forms: 対応可能なOEM剤形
- patent_total: 関連特許の概数（ある場合）

入力：
{INPUT_JSON}

必ず以下のJSON形式のみで返してください。JSON以外のテキストを含めないでください。

{{
  "formula_name": "",
  "formula_summary": "",
  "expected_function": "",
  "mechanism_hypothesis": "",
  "bond_interpretation": [
    {{
      "bond_type": "",
      "atoms": [],
      "explanation": ""
    }}
  ],
  "safety_status": "Green",
  "risk_notes": [],
  "evidence_level": "E1",
  "evidence_needed": [],
  "experiment_suggestions": [],
  "ip_potential": "",
  "product_direction": [],
  "process_direction": [],
  "supplier_requirements": [],
  "regulatory_cautions": [],
  "next_actions": []
}}

ルール：
- 医療効果を確定しない
- 疾病を治す・改善する・防ぐとは言わない
- 小麦アレルギー・セリアック病等に安全とは言わない
- グルテン完全分解とは言わない
- 実験検証前に商品化可能と確定しない
- RedまたはBlackの可能性がある場合は、原材料購入・加工方法・商品化導線を出さない
- Evidenceが弱い場合は必ず「追加検証が必要」と書く
- 食品表示・薬機法・景表法に触れる可能性がある場合は専門家確認を促す
- safety_statusはGreen/Yellow/Red/Blackのいずれか
- evidence_levelはE0/E1/E2/E3/E4/E5のいずれか
- supplier_requirementsには具体的なサプライヤー名・ブランド名・OEM剤形を活用すること
- ip_potentialには特許件数の多い領域は競合密度が高い点を考慮すること
- process_directionにはoem_formsで可能な剤形を具体的に記載すること"""


def _build_atom_context(a: dict) -> dict:
    """Atom から AI プロンプト用の構造化コンテキストを生成する。"""
    ctx: dict = {
        "atom_id":       a["atom_id"],
        "name_ja":       a["name_ja"],
        "name_en":       a["name_en"],
        "atom_type":     a["atom_type"],
        "known_actions": a.get("known_actions", []),
        "possible_bonds": a.get("possible_bonds", []),
        "risk_tags":     a.get("risk_tags", []),
    }

    # PubChem 化合物データ
    compound = a.get("compound", {})
    if compound:
        ctx["compound"] = {
            "molecular_formula": compound.get("molecular_formula"),
            "molecular_weight":  compound.get("molecular_weight"),
            "pubchem_url":       compound.get("pubchem_url"),
        }

    # UniProt 酵素データ
    uniprot = a.get("uniprot", {})
    if uniprot:
        ctx["uniprot"] = {
            "ec_numbers":        uniprot.get("ec_numbers", []),
            "function_comment":  (uniprot.get("function_comment") or "")[:200],
            "catalytic_activity": uniprot.get("catalytic_activity", [])[:1],
        }

    # FDA GRAS ステータス
    gras = a.get("gras", {})
    if gras:
        ctx["gras_status"]  = gras.get("status", "unknown")
        ctx["gras_basis"]   = gras.get("basis", "")
        ctx["jp_regulatory"] = gras.get("jp_status", "不明")

    # PubMed エビデンス（件数 + 上位2件）
    papers = a.get("pubmed_evidence", [])
    ctx["pubmed_evidence_count"] = len(papers)
    if papers:
        ctx["top_papers"] = [
            {
                "title":   p.get("title", "")[:120],
                "journal": p.get("journal", ""),
                "year":    p.get("year", ""),
            }
            for p in papers[:2]
        ]

    # サプライヤー情報
    supplier = a.get("supplier_info", {})
    if supplier:
        ctx["supplier_tier"] = supplier.get("price_tier", "unknown")
        ctx["oem_forms"]     = supplier.get("oem_forms", [])
        ctx["major_suppliers"] = supplier.get("major_suppliers", [])[:2]
        ctx["japan_suppliers"] = supplier.get("japan_suppliers", [])[:2]

    # 特許ランドスケープ
    patents = a.get("patent_landscape", {})
    if patents:
        ctx["patent_total"] = patents.get("total_count", 0)
        ctx["patent_jp"]    = patents.get("jp_count", 0)
        ctx["patent_us"]    = patents.get("us_count", 0)

    # 市場需要 (Google Trends)
    trends = a.get("market_trends", {})
    if trends:
        ctx["market_trend_jp"]  = trends.get("avg_interest_jp", 0)
        ctx["market_trend_us"]  = trends.get("avg_interest_us", 0)
        ctx["trend_direction"]  = trends.get("trend_direction", "")
        ctx["trend_keyword"]    = trends.get("keyword", "")

    # 既存製品数 (Open Food Facts)
    off = a.get("existing_products", {})
    if off:
        ctx["existing_product_count"] = off.get("total_count", 0)
        ctx["top_product_categories"] = off.get("top_categories", [])[:3]

    return ctx


def _build_input_json(fused: FusedFormula, safety: Optional[SafetyGateResult]) -> str:
    data = {
        "atoms": [_build_atom_context(a) for a in fused.atoms],
        "all_risk_tags": fused.all_risk_tags,
        "bond_matches": fused.bond_matches,
        "safety_status":       safety.safety_status if safety else "Unknown",
        "evidence_level":      getattr(safety, "evidence_level", "E0") if safety else "E0",
        "risk_tags_detected":  safety.risk_tags_detected if safety else [],
        "gras_notes":          getattr(safety, "gras_notes", []) if safety else [],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _extract_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group())
    raise ValueError("No JSON found in AI response")


async def analyze_formula(
    fused: FusedFormula,
    safety: Optional[SafetyGateResult],
    ai_provider: str,
    api_key: str,
    model: Optional[str] = None,
) -> AIAnalysisResult:
    input_json = _build_input_json(fused, safety)
    prompt = FORMULA_ANALYSIS_PROMPT.replace("{INPUT_JSON}", input_json)

    raw = await _call_llm(ai_provider, api_key, prompt, model)
    data = _extract_json(raw)
    return AIAnalysisResult(**data)


async def _call_llm(provider: str, api_key: str, prompt: str, model: Optional[str]) -> str:
    if provider == "openai":
        return await _call_openai(api_key, prompt, model or "gpt-4o-mini")
    elif provider == "claude":
        return await _call_claude(api_key, prompt, model or "claude-haiku-4-5-20251001")
    elif provider == "gemini":
        return await _call_gemini(api_key, prompt, model or "gemini-1.5-flash")
    raise ValueError(f"Unknown provider: {provider}")


async def _call_openai(api_key: str, prompt: str, model: str) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return response.choices[0].message.content or ""


async def _call_claude(api_key: str, prompt: str, model: str) -> str:
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.content[0].text


async def _call_gemini(api_key: str, prompt: str, model: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    gmodel = genai.GenerativeModel(model)
    response = gmodel.generate_content(prompt)
    return response.text
