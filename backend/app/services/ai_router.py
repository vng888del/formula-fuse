from __future__ import annotations
import json
import re
from typing import Optional
from app.models.formula import FusedFormula, AIAnalysisResult, SafetyGateResult

FORMULA_ANALYSIS_PROMPT = """あなたはFormula Intelligence Engine（FIE）の解析AIです。
食品・健康食品・発酵・バイオ・素材開発の専門知識を持つコンサルタントとして、
ユーザーが選択したAtomの組み合わせ（フォーミュラ）を多角的に解析してください。

【重要な制約】
あなたは医師・弁護士・規制当局ではありません。
- 医療効果・疾病治癒・予防効果を確定しない
- 食品表示・薬機法・景表法への適合を保証しない
- 実験検証前に商品化可能と確定しない
- 必ず「可能性がある」「検討ポイント」「専門家確認が必要」の形式を使用

【入力データの読み方】
各Atomには以下の情報が含まれます：
- compound: PubChem化合物データ（分子式・分子量・SMILES）
- uniprot: EC番号・酵素機能・触媒反応（酵素Atomのみ）
- gras_status / jp_regulatory: FDA GRAS認証と日本での法的位置づけ
- pubmed_evidence_count: PubMed論文数（E0=0本 〜 E5=100本以上）
- top_papers: 主要論文2件（タイトル・掲載誌・年）
- usda_nutrients: USDAによる主要栄養素データ（energy_kcal, protein_g, fat_g等）
- supplier_tier: 調達コスト (low/medium/high/very_high)
- oem_forms: 対応可能なOEM剤形リスト
- major_suppliers / japan_suppliers: 主要サプライヤー
- market_trend_jp / market_trend_us: Google Trendsスコア（0〜100）
- trend_direction: rising / stable / declining
- existing_product_count: Open Food Factsの既存製品数（市場競争度の指標）

【入力JSON】
{INPUT_JSON}

【出力形式】
必ず以下のJSON形式のみで返してください。JSON以外のテキストを絶対に含めないでください。

{{
  "formula_name": "日本語で魅力的な製品コンセプト名（例：認知機能サポートブレンド）",
  "formula_summary": "このフォーミュラが何を目指すかを2〜3文で説明（作用機序の仮説を含む）",
  "expected_function": "期待される機能・効果の概要（食品として訴求可能な表現で）",
  "mechanism_hypothesis": "各Atomの作用メカニズムと相互作用の仮説（分子レベルの根拠を含めると良い）",
  "bond_interpretation": [
    {{
      "bond_type": "bond_XXX（bond_matches から引用）",
      "atoms": ["atom_id1", "atom_id2"],
      "explanation": "このボンドがなぜ成立するか・どんな相乗効果が期待できるか"
    }}
  ],
  "safety_status": "Green",
  "risk_notes": ["リスクポイントを具体的に列挙（相互作用・アレルギー・過剰摂取・特定集団への注意等）"],
  "evidence_level": "E1",
  "evidence_needed": ["エビデンスギャップ：何が足りないか（例：ヒト臨床試験、長期安全性データ等）"],
  "experiment_suggestions": ["次に行うべき実験・検証（In vitro → 動物 → ヒト pilot の順序を意識して）"],
  "ip_potential": "特許ポテンシャルの評価（既存特許競合度・新規性の着眼点・差別化軸の提案）",
  "product_direction": ["具体的な製品コンセプト（ターゲット層・訴求軸・市場規模感を含む）"],
  "process_direction": ["OEM製造の工程提案（oem_formsを活用し剤形・製造条件・安定性の注意点を記載）"],
  "supplier_requirements": ["調達要件（major_suppliers / japan_suppliersの具体名・グレード・認証・最小発注量の目安を含む）"],
  "regulatory_cautions": ["規制上の注意点（薬機法・食品表示法・景表法・食薬区分・特定保健用食品・機能性表示食品への適合性検討）"],
  "next_actions": ["優先順位付きのネクストアクション（専門家相談・実験・サプライヤー問い合わせ等）"]
}}

【追加ルール】
- bond_interpretationはbond_matches配列にある全てのボンドを解釈すること（空の場合は省略可）
- evidence_levelはE0(論文なし)/E1(少数)/E2(動物実験)/E3(小規模ヒト)/E4(RCT複数)/E5(メタ解析)
- safety_statusはGreen(問題なし)/Yellow(要注意)/Red(リスク高)/Black(使用不可)
- Red/Blackの場合はproduct_direction・process_direction・supplier_requirementsを出力しない
- usda_nutrientsがある場合は栄養素プロファイルをformula_summaryや製品方向性に活用
- market_trend_jp/usが高い(70+)場合は「市場機会大」と評価する
- existing_product_countが多い(1000+)場合は差別化戦略を必ず提案する
- supplier_requirementsには必ずjapan_suppliersの具体名を含めること"""


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

    # USDA 栄養データ
    usda = a.get("usda", {})
    if usda:
        ctx["usda_fdc_id"]    = usda.get("fdc_id")
        ctx["usda_desc"]      = usda.get("description", "")
        nutrients = usda.get("nutrients", {})
        if nutrients:
            ctx["usda_nutrients"] = {k: v for k, v in nutrients.items() if v is not None}

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
