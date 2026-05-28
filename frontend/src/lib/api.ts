import type {
  Atom, FusedFormula, AIAnalysisResult, SafetyGateResult, SavedFormula, ApiKeyConfig, BondRule
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface HealthStatus {
  status: string;
  version: string;
  db: {
    mode: "postgresql" | "supabase" | "memory" | "none";
    status: "connected" | "error" | "pending" | "in_memory" | "not_configured";
    persistent: boolean;
  };
  data: {
    atoms: number;
  };
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request<HealthStatus>("/health"),

  atoms: {
    list: () => request<Atom[]>("/atoms"),
    get: (id: string) => request<Atom>(`/atoms/${id}`),
    search: (q: string) => request<Atom[]>(`/atoms/search?q=${encodeURIComponent(q)}`),
    byCategory: (cat: string) => request<Atom[]>(`/atoms/category/${cat}`),
    bondRules: () => request<BondRule[]>("/atoms/meta/bond-rules"),
    riskTags: () => request<unknown[]>("/atoms/meta/risk-tags"),
  },

  formula: {
    fuse: (atomIds: string[]) =>
      request<FusedFormula>("/formula/fuse", {
        method: "POST",
        body: JSON.stringify({ atom_ids: atomIds }),
      }),

    safetyGate: (atomIds: string[]) =>
      request<SafetyGateResult>("/formula/safety-gate", {
        method: "POST",
        body: JSON.stringify({ atom_ids: atomIds }),
      }),

    analyze: (fused: FusedFormula, apiKey: ApiKeyConfig, model?: string) =>
      request<AIAnalysisResult>("/formula/analyze", {
        method: "POST",
        headers: { "X-AI-Provider-Key": apiKey.key },
        body: JSON.stringify({
          fused_formula: fused,
          ai_provider: apiKey.provider,
          model: model || undefined,
        }),
      }),

    save: (data: {
      name: string;
      atom_ids: string[];
      fused_formula?: FusedFormula;
      ai_analysis?: AIAnalysisResult;
      safety_result?: SafetyGateResult;
    }) =>
      request<SavedFormula>("/formula/save", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    history: () => request<SavedFormula[]>("/formula/history"),
    get: (id: string) => request<SavedFormula>(`/formula/history/${id}`),
    reportUrl: (id: string) => `${BASE_URL}/formula/history/${id}/report`,
  },
};
