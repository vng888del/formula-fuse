"use client";
import type { AIAnalysisResult, SafetyGateResult, FusedFormula } from "@/types";
import { api } from "@/lib/api";

interface Props {
  analysis: AIAnalysisResult | null;
  safety: SafetyGateResult | null;
  fused: FusedFormula | null;
  formulaId: string | null;
  onSave: () => void;
  saving: boolean;
}

const SAFETY_CONFIG = {
  Green:  { color: "var(--green)",  label: "High",    emoji: "✅" },
  Yellow: { color: "var(--gold)",   label: "Medium",  emoji: "⚠️" },
  Red:    { color: "#f44336",       label: "Low",     emoji: "🔴" },
  Black:  { color: "#9e9e9e",       label: "Blocked", emoji: "⛔" },
};

const EV_SCORE: Record<string, number> = {
  E0: 5, E1: 20, E2: 40, E3: 60, E4: 80, E5: 95,
};

export function AIReactionPanel({ analysis, safety, fused, formulaId, onSave, saving }: Props) {
  if (!analysis) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-4 px-6"
        style={{ background: "var(--bg-secondary)" }}>
        <div className="w-16 h-16 rounded-full flex items-center justify-center"
          style={{ background: "rgba(79,195,247,0.06)", border: "1px solid rgba(79,195,247,0.15)" }}>
          <svg className="w-7 h-7" style={{ color: "rgba(79,195,247,0.4)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <div className="text-center">
          <p className="text-sm font-medium" style={{ color: "rgba(255,255,255,0.5)" }}>AI Analysis</p>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            AtomをFuseして<br />解析結果を表示
          </p>
        </div>
      </div>
    );
  }

  const safetyCfg = SAFETY_CONFIG[analysis.safety_status] || SAFETY_CONFIG.Yellow;
  const evScore = EV_SCORE[analysis.evidence_level] || 10;

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-secondary)" }}>
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          <span className="text-xs" style={{ color: "var(--blue)" }}>✦</span>
          <h2 className="text-[10px] font-bold tracking-widest uppercase" style={{ color: "var(--text-secondary)" }}>
            AI Analysis
          </h2>
        </div>
        <span className="text-[9px] px-2 py-0.5 rounded-full font-semibold tracking-wide"
          style={{ background: "rgba(105,240,174,0.1)", color: "var(--green)", border: "1px solid rgba(105,240,174,0.2)" }}>
          ANALYSIS COMPLETE
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Formula name + summary */}
        <div className="px-4 py-4" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-base font-bold leading-tight" style={{ color: "var(--text-primary)" }}>
              {analysis.formula_name || "Formula"}
            </h3>
            {formulaId && (
              <button className="shrink-0 text-[10px] mt-0.5 opacity-40 hover:opacity-70 transition-opacity"
                style={{ color: "var(--text-secondary)" }}>
                ⎘
              </button>
            )}
          </div>
          <p className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
            {analysis.formula_summary}
          </p>
        </div>

        {/* Key metrics */}
        <div className="px-4 py-4 space-y-4">
          {/* Expected Function */}
          {analysis.expected_function && (
            <Section icon="🌿" label="EXPECTED FUNCTION">
              <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.65)" }}>
                {analysis.expected_function}
              </p>
            </Section>
          )}

          {/* Safety Status */}
          <Section icon="🛡️" label="SAFETY STATUS" valueColor={safetyCfg.color} value={safetyCfg.label}>
            <p className="text-xs" style={{ color: "rgba(255,255,255,0.5)" }}>
              {analysis.risk_notes[0] || "評価完了。専門家確認を推奨します。"}
            </p>
            {analysis.risk_notes.length > 1 && (
              <details className="mt-1">
                <summary className="text-[9px] cursor-pointer" style={{ color: "var(--text-muted)" }}>
                  +{analysis.risk_notes.length - 1} more risks
                </summary>
                <ul className="mt-1 space-y-0.5">
                  {analysis.risk_notes.slice(1).map((n, i) => (
                    <li key={i} className="text-[9px]" style={{ color: "rgba(255,255,255,0.4)" }}>• {n}</li>
                  ))}
                </ul>
              </details>
            )}
          </Section>

          {/* Safety Gate details */}
          {safety && ((safety.gras_notes && safety.gras_notes.length > 0) || (safety.atom_safety_notes && safety.atom_safety_notes.length > 0)) && (
            <Section icon="🔬" label="SAFETY GATE">
              {safety.gras_notes && safety.gras_notes.length > 0 && (
                <div className="space-y-1 mb-2">
                  {safety.gras_notes.map((note, i) => (
                    <div key={i} className="flex items-start gap-1.5 rounded-lg px-2 py-1.5"
                      style={{ background: "rgba(255,152,0,0.06)", border: "1px solid rgba(255,152,0,0.15)" }}>
                      <span className="text-[10px] shrink-0" style={{ color: "rgba(255,152,0,0.8)" }}>⚠</span>
                      <span className="text-[10px]" style={{ color: "rgba(255,152,0,0.7)" }}>{note}</span>
                    </div>
                  ))}
                </div>
              )}
              {safety.atom_safety_notes && safety.atom_safety_notes.length > 0 && (
                <details>
                  <summary className="text-[9px] cursor-pointer select-none" style={{ color: "var(--text-muted)" }}>
                    Atom別安全メモ ({safety.atom_safety_notes.length}件)
                  </summary>
                  <div className="mt-1.5 space-y-1">
                    {safety.atom_safety_notes.map((n) => (
                      <div key={n.atom_id} className="rounded px-2 py-1" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-[9px] font-semibold" style={{ color: "rgba(255,255,255,0.6)" }}>{n.name}</span>
                          <span className="text-[8px] px-1 rounded" style={{ background: "rgba(79,195,247,0.1)", color: "var(--blue)" }}>
                            {n.evidence_count}件
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[8px]" style={{ color: "var(--text-muted)" }}>{n.gras_status}</span>
                          {n.jp_status && <span className="text-[8px]" style={{ color: "var(--text-muted)" }}>JP: {n.jp_status}</span>}
                        </div>
                        {n.safety_note && (
                          <p className="text-[9px] mt-0.5" style={{ color: "rgba(255,152,0,0.7)" }}>{n.safety_note}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </Section>
          )}

          {/* Evidence strength */}
          <Section icon="📊" label="EVIDENCE STRENGTH" valueColor="var(--blue)" value={`${evScore}%`}>
            <div className="flex items-center gap-2 mt-1">
              <div className="flex-1 progress-track h-1.5 rounded-full">
                <div
                  className="h-1.5 rounded-full transition-all"
                  style={{ width: `${evScore}%`, background: `linear-gradient(90deg, var(--blue), var(--purple))` }}
                />
              </div>
              <span className="text-[9px] shrink-0" style={{ color: "var(--text-muted)" }}>
                {analysis.evidence_level}
              </span>
            </div>
            {analysis.evidence_needed.length > 0 && (
              <p className="text-[9px] mt-1" style={{ color: "rgba(255,255,255,0.35)" }}>
                {analysis.evidence_needed[0]}
              </p>
            )}
          </Section>

          {/* IP Potential */}
          {analysis.ip_potential && (
            <Section icon="🔒" label="IP POTENTIAL" valueColor="var(--green)" value="High">
              <p className="text-xs" style={{ color: "rgba(255,255,255,0.5)" }}>
                {analysis.ip_potential}
              </p>
            </Section>
          )}

          {/* Mechanism */}
          {analysis.mechanism_hypothesis && (
            <Section icon="⚗️" label="MECHANISM">
              <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.55)" }}>
                {analysis.mechanism_hypothesis}
              </p>
            </Section>
          )}

          {/* Regulatory */}
          {analysis.regulatory_cautions.length > 0 && (
            <Section icon="⚠️" label="REGULATORY NOTES">
              <ul className="space-y-1">
                {analysis.regulatory_cautions.slice(0, 3).map((r, i) => (
                  <li key={i} className="text-xs" style={{ color: "rgba(255,152,0,0.8)" }}>• {r}</li>
                ))}
              </ul>
            </Section>
          )}
        </div>

        {/* Next actions */}
        {analysis.next_actions.length > 0 && (
          <div className="px-4 pb-4">
            <h4 className="text-[9px] font-bold tracking-widest uppercase mb-2" style={{ color: "var(--text-muted)" }}>
              Next Actions
            </h4>
            <div className="space-y-1.5">
              {analysis.next_actions.slice(0, 4).map((action, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-lg px-3 py-2 cursor-pointer group transition-colors"
                  style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span className="text-[9px] shrink-0" style={{ color: "var(--text-muted)" }}>
                      {["📋","📈","💾","🔬"][i] || "→"}
                    </span>
                    <span className="text-xs truncate" style={{ color: "rgba(255,255,255,0.6)" }}>{action}</span>
                  </div>
                  <svg className="w-3 h-3 shrink-0 opacity-30 group-hover:opacity-70 transition-opacity"
                    style={{ color: "var(--text-secondary)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Disclaimer */}
        <div className="px-4 pb-4">
          <p className="text-[8px] leading-relaxed" style={{ color: "var(--text-muted)", opacity: 0.6 }}>
            このAI出力は研究補助目的です。医療効果・安全性・特許性の確定的判断ではありません。
          </p>
        </div>
      </div>

      {/* Export button */}
      <div className="shrink-0 p-4 space-y-2" style={{ borderTop: "1px solid var(--border)" }}>
        <button
          onClick={onSave}
          disabled={saving}
          className="w-full py-2.5 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all"
          style={{
            background: "rgba(105,240,174,0.1)",
            border: "1px solid rgba(105,240,174,0.2)",
            color: "var(--green)",
          }}
        >
          {saving ? "保存中..." : "💾 Save Formula"}
        </button>
        {formulaId && (
          <a
            href={api.formula.reportUrl(formulaId)}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full py-2.5 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all btn-neon"
            style={{ color: "white" }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            EXPORT REPORT
          </a>
        )}
      </div>
    </div>
  );
}

function Section({ icon, label, value, valueColor, children }: {
  icon: string; label: string; value?: string; valueColor?: string; children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-xs">{icon}</span>
          <span className="text-[9px] font-bold tracking-widest uppercase" style={{ color: "var(--text-muted)" }}>
            {label}
          </span>
        </div>
        {value && (
          <span className="text-xs font-bold" style={{ color: valueColor || "var(--text-primary)" }}>
            {value}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}
