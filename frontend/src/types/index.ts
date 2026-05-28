export type AtomType = "ingredient" | "microbe" | "enzyme" | "condition" | "goal" | "process";

// ── Phase 1–5 エンリッチメントデータ型 ────────────────────────────────────────

export interface CompoundData {
  pubchem_cid?: number;
  molecular_formula?: string;
  molecular_weight?: string | number;
  smiles?: string;
  inchikey?: string;
  pubchem_url?: string;
}

export interface UniprotData {
  uniprot_id?: string;
  protein_name?: string;
  gene_names?: string[];
  organism?: string;
  ec_numbers?: string[];
  function_comment?: string;
  subcellular_location?: string[];
  catalytic_activity?: string[];
  uniprot_url?: string;
  taxonomy_id?: number;
  lineage?: string[];
}

export interface GrasData {
  status: "GRAS" | "NDI" | "food_additive" | "unknown";
  basis?: string;
  notes?: string;
  jp_status?: string;
}

export interface PubmedPaper {
  pmid: string;
  title: string;
  authors: string[];
  journal: string;
  year: string;
  pubmed_url: string;
}

export interface SupplierInfo {
  major_suppliers: string[];
  japan_suppliers: string[];
  oem_forms: string[];
  typical_grade?: string;
  certifications?: string[];
  price_tier?: "low" | "medium" | "high" | "very_high";
  lead_time_weeks?: number;
  min_order_qty?: string;
  notes?: string;
}

export interface PatentLandscape {
  query: string;
  total_count: number;
  jp_count: number;
  us_count: number;
  top_patents?: Array<{
    lens_id: string;
    title: string;
    applicant: string;
    year: string;
    jurisdictions: string[];
    lens_url: string;
  }>;
  retrieved_at: string;
}

export interface MarketTrends {
  keyword: string;
  geo: string;
  timeframe: string;
  avg_interest_jp: number;
  avg_interest_us: number;
  avg_interest_ww: number;
  trend_direction: "rising" | "stable" | "declining";
  peak_month_jp?: string;
  retrieved_at: string;
}

export interface ExistingProducts {
  search_query: string;
  total_count: number;
  sample_products: Array<{
    product_name: string;
    brand: string;
    categories: string[];
    countries: string[];
    nutriscore?: string;
    image_url?: string;
    off_url?: string;
  }>;
  top_categories: string[];
  top_countries: string[];
  retrieved_at: string;
}

// ── Atom ───────────────────────────────────────────────────────────────────────

export interface Atom {
  atom_id: string;
  name_ja: string;
  name_en: string;
  atom_type: AtomType;
  category: string;
  domain: string;
  known_actions: string[];
  possible_bonds: string[];
  risk_tags: string[];
  evidence_keywords: string[];
  regulatory_notes: string[];
  process_keywords: string[];
  supplier_keywords: string[];
  // enrichment fields (Phase 1–5)
  compound?: CompoundData;
  uniprot?: UniprotData;
  gras?: GrasData;
  usda?: Record<string, unknown>;
  pubmed_evidence?: PubmedPaper[];
  supplier_info?: SupplierInfo;
  patent_landscape?: PatentLandscape;
  market_trends?: MarketTrends;
  existing_products?: ExistingProducts;
}

// ── Safety & Analysis ──────────────────────────────────────────────────────────

export type SafetyStatus = "Green" | "Yellow" | "Red" | "Black";
export type EvidenceLevel = "E0" | "E1" | "E2" | "E3" | "E4" | "E5";

export interface AtomSafetyNote {
  atom_id: string;
  name: string;
  gras_status: string;
  jp_status: string;
  evidence_count: number;
  ec_numbers?: string[];
  molecular_weight?: number;
  safety_note?: string;
}

export interface BondInterpretation {
  bond_type: string;
  atoms: string[];
  explanation: string;
}

export interface AIAnalysisResult {
  formula_name: string;
  formula_summary: string;
  expected_function: string;
  mechanism_hypothesis: string;
  bond_interpretation: BondInterpretation[];
  safety_status: SafetyStatus;
  risk_notes: string[];
  evidence_level: EvidenceLevel;
  evidence_needed: string[];
  experiment_suggestions: string[];
  ip_potential: string;
  product_direction: string[];
  process_direction: string[];
  supplier_requirements: string[];
  regulatory_cautions: string[];
  next_actions: string[];
}

export interface SafetyGateResult {
  safety_status: SafetyStatus;
  blocking_reasons: string[];
  risk_tags_detected: string[];
  allowed_actions: string[];
  restricted_actions: string[];
  required_expert_reviews: string[];
  safe_alternative_direction: string[];
  // Phase 3 additions
  evidence_level?: EvidenceLevel;
  gras_notes?: string[];
  atom_safety_notes?: AtomSafetyNote[];
}

// ── Formula ────────────────────────────────────────────────────────────────────

export interface FusedFormula {
  atom_ids: string[];
  atoms: Atom[];
  all_risk_tags: string[];
  all_possible_bonds: string[];
  bond_matches: BondMatch[];
}

export interface BondMatch {
  bond_rule_id: string;
  bond_type: string;
  source_atom: string;
  target_atom: string;
  expected_result: string;
  confidence: string;
  risk_level: string;
  explanation: string;
}

export interface SavedFormula {
  id: string;
  name: string;
  atom_ids: string[];
  fused_formula?: FusedFormula;
  ai_analysis?: AIAnalysisResult;
  safety_result?: SafetyGateResult;
  created_at?: string;
}

export interface ApiKeyConfig {
  provider: "openai" | "claude" | "gemini";
  key: string;
}

export interface BondRule {
  bond_rule_id: string;
  source_atom_type: string;
  target_atom_type: string;
  source_required_tags: string[];
  target_required_tags: string[];
  bond_type: string;
  expected_result: string;
  confidence: "high" | "medium" | "low";
  risk_level: "green" | "yellow" | "red";
  explanation: string;
  required_checks: string[];
}
