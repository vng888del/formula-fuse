"use client";
import { useState, useEffect } from "react";
import type { Atom, DoseGuideResult, AtomDoseGuide } from "@/types";
import { api } from "@/lib/api";

interface Props {
  selectedAtoms: Atom[];
  onClose: () => void;
}

function fmtMg(mg: number): string {
  if (mg >= 1e9) return `${(mg / 1e9).toFixed(0)}B CFU`;
  if (mg >= 1000) return `${(mg / 1000).toFixed(mg >= 10000 ? 0 : 1)}g`;
  return `${mg.toFixed(mg < 1 ? 2 : 0)}mg`;
}

function DoseBar({ guide }: { guide: AtomDoseGuide }) {
  const range = guide.dose_range_max_mg - guide.dose_range_min_mg || 1;
  const pct = Math.min(100, ((guide.suggested_dose_mg - guide.dose_range_min_mg) / range) * 100);
  const basisColor = guide.dose_basis === "臨床試験" ? "#69f0ae" : guide.dose_basis.includes("ISSN") ? "#69f0ae" : "#4fc3f7";

  return (
    <div className="rounded-xl px-3 py-2.5" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold leading-tight" style={{ color: "var(--text-primary)" }}>{guide.name_ja}</p>
          <p className="text-[8px] truncate" style={{ color: "var(--text-muted)" }}>{guide.name_en}</p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-xs font-bold" style={{ color: basisColor }}>{fmtMg(guide.suggested_dose_mg)}</p>
          <p className="text-[8px]" style={{ color: "var(--text-muted)" }}>{fmtMg(guide.dose_range_min_mg)}–{fmtMg(guide.dose_range_max_mg)}</p>
        </div>
      </div>

      {/* Dose bar */}
      <div className="h-1 rounded-full mb-1.5" style={{ background: "rgba(255,255,255,0.06)" }}>
        <div className="h-1 rounded-full" style={{ width: `${pct}%`, background: basisColor, opacity: 0.7 }} />
      </div>

      {/* Basis tag + form */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-[8px] px-1.5 py-0.5 rounded-full font-bold"
          style={{ background: `${basisColor}15`, color: basisColor, border: `1px solid ${basisColor}30` }}>
          {guide.dose_basis}
        </span>
        <span className="text-[8px]" style={{ color: "var(--text-muted)" }}>{guide.typical_form}</span>
      </div>

      {/* Notes */}
      {guide.key_notes.length > 0 && (
        <div className="mt-1.5 space-y-0.5">
          {guide.key_notes.slice(0, 2).map((n, i) => (
            <p key={i} className="text-[8px] leading-relaxed" style={{ color: "rgba(255,255,255,0.4)" }}>• {n}</p>
          ))}
        </div>
      )}
    </div>
  );
}

export function DosePanel({ selectedAtoms, onClose }: Props) {
  const [result, setResult] = useState<DoseGuideResult | null>(null);
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    if (selectedAtoms.length === 0) return;
    setLoading(true);
    try {
      const r = await api.formula.doseGuide(selectedAtoms.map(a => a.atom_id));
      setResult(r);
    } catch { /* silently fail */ } finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [selectedAtoms.length]);

  if (selectedAtoms.length === 0) {
    return (
      <div className="flex flex-col h-full items-center justify-center px-6"
        style={{ background: "var(--bg-secondary)" }}>
        <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
          Atomを選択すると配合量ガイドを表示します
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-secondary)", fontSize: 11 }}>
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between shrink-0"
        style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          <span>📐</span>
          <div>
            <p className="font-bold text-xs" style={{ color: "var(--text-primary)" }}>配合量ガイド</p>
            <p className="text-[9px]" style={{ color: "var(--text-muted)" }}>臨床推奨投与量</p>
          </div>
        </div>
        <button onClick={onClose} className="w-6 h-6 flex items-center justify-center rounded-full"
          style={{ color: "var(--text-muted)", background: "rgba(255,255,255,0.05)" }}>×</button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {loading && (
          <div className="flex justify-center py-4">
            <div className="w-5 h-5 rounded-full border-2 animate-spin"
              style={{ borderColor: "var(--blue)", borderTopColor: "transparent" }} />
          </div>
        )}

        {result && !loading && (
          <>
            {/* Summary */}
            <div className="rounded-xl p-3 text-center" style={{ background: "rgba(79,195,247,0.06)", border: "1px solid rgba(79,195,247,0.15)" }}>
              <p className="text-[9px] font-bold tracking-widest uppercase mb-1" style={{ color: "var(--blue)" }}>
                DAILY SERVING
              </p>
              <p className="text-base font-bold" style={{ color: "var(--text-primary)" }}>{result.serving_summary.replace("推奨総量: ", "")}</p>
              <p className="text-[9px] mt-1" style={{ color: "var(--text-muted)" }}>{selectedAtoms.length}種のAtom配合</p>
            </div>

            {/* Per-atom guides */}
            <div>
              <p className="text-[9px] font-bold tracking-widest uppercase mb-2" style={{ color: "var(--text-muted)" }}>
                Atom別 推奨配合量
              </p>
              <div className="space-y-1.5">
                {result.atom_guides.map(g => <DoseBar key={g.atom_id} guide={g} />)}
              </div>
            </div>

            {/* Formulation notes */}
            {result.formulation_notes.length > 0 && (
              <div>
                <p className="text-[9px] font-bold tracking-widest uppercase mb-1.5" style={{ color: "var(--text-muted)" }}>
                  製剤上の注意
                </p>
                <div className="space-y-1">
                  {result.formulation_notes.map((n, i) => (
                    <p key={i} className="text-[9px] leading-relaxed" style={{ color: "rgba(255,255,255,0.4)" }}>• {n}</p>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
