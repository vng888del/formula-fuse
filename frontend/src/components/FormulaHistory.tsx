"use client";
import { useEffect, useState } from "react";
import type { SavedFormula } from "@/types";
import { api } from "@/lib/api";

const SAFETY_COLOR: Record<string, string> = {
  Green:  "rgba(105,240,174,0.8)",
  Yellow: "rgba(255,213,79,0.8)",
  Red:    "rgba(244,67,54,0.8)",
  Black:  "rgba(255,255,255,0.3)",
};
const SAFETY_BG: Record<string, string> = {
  Green:  "rgba(105,240,174,0.08)",
  Yellow: "rgba(255,213,79,0.08)",
  Red:    "rgba(244,67,54,0.08)",
  Black:  "rgba(255,255,255,0.04)",
};

interface Props {
  onSelect: (f: SavedFormula) => void;
}

export function FormulaHistory({ onSelect }: Props) {
  const [formulas, setFormulas] = useState<SavedFormula[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.formula.history()
      .then(setFormulas)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <div className="w-4 h-4 rounded-full border-2 border-t-transparent animate-spin"
          style={{ borderColor: "var(--blue)", borderTopColor: "transparent" }} />
      </div>
    );
  }

  if (formulas.length === 0) {
    return (
      <div className="text-center py-6">
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>保存されたFormulaはありません</p>
      </div>
    );
  }

  return (
    <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
      {formulas.map((f) => {
        const status = f.ai_analysis?.safety_status;
        return (
          <button
            key={f.id}
            onClick={() => onSelect(f)}
            className="shrink-0 flex flex-col gap-1.5 rounded-xl px-3 py-2.5 text-left transition-all hover:scale-[1.02] active:scale-[0.98]"
            style={{
              width: 180,
              background: status ? SAFETY_BG[status] : "rgba(255,255,255,0.03)",
              border: `1px solid ${status ? SAFETY_COLOR[status].replace("0.8", "0.2") : "var(--border)"}`,
            }}
          >
            <div className="flex items-center justify-between gap-1">
              <span className="text-xs font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                {f.name || "Untitled"}
              </span>
              {status && (
                <span className="text-[8px] shrink-0 px-1.5 py-0.5 rounded-full font-bold"
                  style={{ background: SAFETY_BG[status], color: SAFETY_COLOR[status], border: `1px solid ${SAFETY_COLOR[status].replace("0.8", "0.25")}` }}>
                  {status}
                </span>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>
                {f.atom_ids.length} atoms
                {f.ai_analysis?.evidence_level && ` · ${f.ai_analysis.evidence_level}`}
              </span>
              {f.created_at && (
                <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>
                  {new Date(f.created_at).toLocaleDateString("ja-JP", { month: "short", day: "numeric" })}
                </span>
              )}
            </div>
            <a
              href={api.formula.reportUrl(f.id)}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-[9px] self-end transition-opacity hover:opacity-100 opacity-50"
              style={{ color: "var(--blue)" }}
            >
              📄 レポート →
            </a>
          </button>
        );
      })}
    </div>
  );
}
