"use client";
import { useState } from "react";
import type { Atom, SuggestResult, SuggestedAtom } from "@/types";
import { api } from "@/lib/api";
import { ATOM_TYPE_CONFIG } from "@/lib/atomColors";

const TIER_COLOR: Record<string, string> = {
  low:       "#69f0ae",
  medium:    "#4fc3f7",
  high:      "#ffd54f",
  very_high: "#ef5350",
  unknown:   "rgba(255,255,255,0.3)",
};

const QUICK_GOALS = [
  "睡眠改善", "認知機能・集中力", "ストレス軽減", "腸活・腸内環境",
  "スポーツパフォーマンス", "免疫サポート", "美肌・コラーゲン", "抗老化・長寿",
  "抗炎症", "エネルギー・疲労回復", "関節サポート", "代謝・血糖",
];

interface Props {
  allAtoms: Atom[];
  onAddAtoms: (atoms: Atom[]) => void;
  onClose: () => void;
}

export function SuggestPanel({ allAtoms, onAddAtoms, onClose }: Props) {
  const [goal, setGoal] = useState("");
  const [result, setResult] = useState<SuggestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const search = async (g: string) => {
    if (!g.trim()) return;
    setLoading(true); setError(""); setResult(null); setSelected(new Set());
    try {
      const r = await api.formula.suggest(g.trim(), 8);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラー");
    } finally {
      setLoading(false);
    }
  };

  const toggle = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const addSelected = () => {
    const atoms = allAtoms.filter(a => selected.has(a.atom_id));
    if (atoms.length > 0) {
      onAddAtoms(atoms);
      onClose();
    }
  };

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-secondary)", fontSize: 11 }}>
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          <span style={{ color: "var(--blue)" }}>🎯</span>
          <div>
            <p className="font-bold text-xs" style={{ color: "var(--text-primary)" }}>目的からAtomを提案</p>
            <p className="text-[9px]" style={{ color: "var(--text-muted)" }}>Reverse Formula Search</p>
          </div>
        </div>
        <button onClick={onClose} className="w-6 h-6 flex items-center justify-center rounded-full"
          style={{ color: "var(--text-muted)", background: "rgba(255,255,255,0.05)" }}>×</button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Search input */}
        <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex gap-2">
            <input
              type="text"
              value={goal}
              onChange={e => setGoal(e.target.value)}
              onKeyDown={e => e.key === "Enter" && search(goal)}
              placeholder="例：睡眠改善、認知機能サポート、スポーツパフォーマンス"
              className="flex-1 rounded-lg px-3 py-1.5 text-xs outline-none"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border-bright)", color: "var(--text-primary)" }}
            />
            <button
              onClick={() => search(goal)}
              disabled={loading || !goal.trim()}
              className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all"
              style={{ background: "rgba(79,195,247,0.15)", border: "1px solid rgba(79,195,247,0.3)", color: "var(--blue)" }}
            >
              {loading ? "..." : "提案"}
            </button>
          </div>

          {/* Quick goals */}
          <div className="mt-2 flex flex-wrap gap-1">
            {QUICK_GOALS.map(g => (
              <button key={g} onClick={() => { setGoal(g); search(g); }}
                className="px-2 py-0.5 rounded-full text-[9px] transition-all"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
                {g}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="mx-4 mt-3 px-3 py-2 rounded-lg text-xs" style={{ background: "rgba(244,67,54,0.08)", color: "#f44336", border: "1px solid rgba(244,67,54,0.2)" }}>
            {error}
          </div>
        )}

        {result && (
          <div className="px-4 py-3 space-y-3">
            {/* Formula concept */}
            <div className="rounded-xl px-3 py-2.5" style={{ background: "rgba(79,195,247,0.06)", border: "1px solid rgba(79,195,247,0.15)" }}>
              <p className="text-[9px] font-bold tracking-widest uppercase mb-1" style={{ color: "var(--blue)" }}>FORMULA CONCEPT</p>
              <p className="text-xs" style={{ color: "var(--text-primary)" }}>{result.formula_concept}</p>
            </div>

            {/* Suggested atoms */}
            <div>
              <p className="text-[9px] font-bold tracking-widest uppercase mb-2" style={{ color: "var(--text-muted)" }}>
                推奨 Atom（{result.suggested_atoms.length}件）
              </p>
              <div className="space-y-1.5">
                {result.suggested_atoms.map(a => (
                  <SuggestedAtomCard
                    key={a.atom_id}
                    atom={a}
                    selected={selected.has(a.atom_id)}
                    onToggle={() => toggle(a.atom_id)}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Add button */}
      {selected.size > 0 && (
        <div className="shrink-0 px-4 py-3" style={{ borderTop: "1px solid var(--border)" }}>
          <button
            onClick={addSelected}
            className="w-full py-2.5 rounded-xl text-sm font-bold btn-neon flex items-center justify-center gap-2"
          >
            <span>+</span>
            {selected.size}件のAtomを追加してFuse
          </button>
        </div>
      )}
    </div>
  );
}

function SuggestedAtomCard({ atom, selected, onToggle }: {
  atom: SuggestedAtom; selected: boolean; onToggle: () => void;
}) {
  const cfg = ATOM_TYPE_CONFIG[atom.atom_type as keyof typeof ATOM_TYPE_CONFIG] || ATOM_TYPE_CONFIG.ingredient;
  const tierColor = TIER_COLOR[atom.price_tier] || TIER_COLOR.unknown;

  return (
    <button
      onClick={onToggle}
      className="w-full rounded-xl px-3 py-2.5 text-left transition-all"
      style={{
        background: selected ? `${cfg.color}0a` : "rgba(255,255,255,0.02)",
        border: `1px solid ${selected ? cfg.color : "var(--border)"}`,
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="w-4 h-4 rounded-full shrink-0 flex items-center justify-center"
            style={{ background: selected ? cfg.color : "rgba(255,255,255,0.08)", border: `1px solid ${selected ? cfg.color : "var(--border)"}` }}>
            {selected && <span style={{ fontSize: 8, color: "black" }}>✓</span>}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold leading-tight" style={{ color: selected ? cfg.color : "var(--text-primary)" }}>
              {atom.name_ja}
            </p>
            <p className="text-[9px] truncate" style={{ color: "var(--text-muted)" }}>{atom.name_en}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {/* Relevance score */}
          <div className="rounded px-1 py-0.5" style={{ background: "rgba(79,195,247,0.1)", border: "1px solid rgba(79,195,247,0.2)" }}>
            <span className="text-[8px] font-bold" style={{ color: "var(--blue)" }}>{atom.relevance_score}pt</span>
          </div>
          {/* Price tier */}
          <div className="w-2 h-2 rounded-full" style={{ background: tierColor }} title={atom.price_tier} />
        </div>
      </div>

      {/* Match reasons */}
      {atom.match_reasons.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {atom.match_reasons.map((r, i) => (
            <span key={i} className="text-[8px] px-1.5 py-0.5 rounded-full"
              style={{ background: "rgba(255,255,255,0.04)", color: "rgba(255,255,255,0.4)", border: "1px solid var(--border)" }}>
              {r}
            </span>
          ))}
        </div>
      )}

      {/* Stats row */}
      <div className="mt-1.5 flex items-center gap-2">
        <span className="text-[8px]" style={{ color: "var(--text-muted)" }}>
          PubMed {atom.pubmed_count}件
        </span>
        <span className="text-[8px]" style={{ color: "var(--text-muted)" }}>
          Bond {atom.bond_count}ルール
        </span>
        <span className="text-[8px]" style={{ color: tierColor }}>
          {atom.price_tier}
        </span>
      </div>
    </button>
  );
}
