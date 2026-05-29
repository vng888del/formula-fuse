"use client";
import { useState, useMemo } from "react";
import type { Atom } from "@/types";
import { AtomCard } from "./AtomCard";
import { AtomDetailPanel } from "./AtomDetailPanel";

const FILTERS = [
  { value: "all", label: "All" },
  { value: "ingredient", label: "原材料" },
  { value: "microbe", label: "菌" },
  { value: "enzyme", label: "酵素" },
  { value: "condition", label: "条件" },
  { value: "goal", label: "目的" },
];

interface Props {
  atoms: Atom[];
  selectedIds: string[];
  onToggle: (atom: Atom) => void;
}

export function AtomLibrary({ atoms, selectedIds, onToggle }: Props) {
  const [category, setCategory] = useState("all");
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [detailAtom, setDetailAtom] = useState<Atom | null>(null);

  const filtered = useMemo(() => {
    return atoms.filter((a) => {
      const catOk = category === "all" || a.atom_type === category;
      const q = query.toLowerCase();
      const textOk = !q ||
        a.name_ja.includes(q) ||
        a.name_en.toLowerCase().includes(q) ||
        a.category.toLowerCase().includes(q) ||
        a.known_actions.some(act => act.toLowerCase().includes(q)) ||
        a.possible_bonds.some(b => b.toLowerCase().includes(q));
      return catOk && textOk;
    });
  }, [atoms, category, query]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: atoms.length };
    for (const a of atoms) {
      c[a.atom_type] = (c[a.atom_type] || 0) + 1;
    }
    return c;
  }, [atoms]);

  if (detailAtom) {
    return <AtomDetailPanel atom={detailAtom} onClose={() => setDetailAtom(null)} />;
  }

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-secondary)" }}>
      <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid var(--border)" }}>
        <div>
          <h2 className="text-[10px] font-bold tracking-widest uppercase" style={{ color: "var(--text-secondary)" }}>
            Atom Library
          </h2>
          <p className="text-[9px] mt-0.5" style={{ color: "var(--text-muted)" }}>
            Ingredients & Parameters
          </p>
        </div>
        <button
          onClick={() => setSearching(!searching)}
          className="w-7 h-7 flex items-center justify-center rounded-lg transition-colors"
          style={{ color: searching ? "var(--blue)" : "var(--text-muted)", background: searching ? "rgba(79,195,247,0.1)" : "transparent" }}
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>
      </div>

      {searching && (
        <div className="px-3 py-2" style={{ borderBottom: "1px solid var(--border)" }}>
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="名前・機能・ボンドタイプで検索..."
            className="w-full rounded-lg px-3 py-1.5 text-xs outline-none"
            style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border-bright)", color: "var(--text-primary)" }}
          />
        </div>
      )}

      <div className="px-3 py-2 flex flex-wrap gap-1" style={{ borderBottom: "1px solid var(--border)" }}>
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setCategory(f.value)}
            className="px-2 py-0.5 rounded-full text-[10px] font-medium transition-all flex items-center gap-1"
            style={{
              background: category === f.value ? "rgba(79,195,247,0.15)" : "transparent",
              border: `1px solid ${category === f.value ? "rgba(79,195,247,0.4)" : "var(--border)"}`,
              color: category === f.value ? "var(--blue)" : "var(--text-muted)",
            }}
          >
            {f.label}
            {counts[f.value] != null && (
              <span className="text-[8px] opacity-60">{counts[f.value]}</span>
            )}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3">
        <div className="grid grid-cols-2 gap-4">
          {filtered.map((atom) => (
            <AtomCard
              key={atom.atom_id}
              atom={atom}
              selected={selectedIds.includes(atom.atom_id)}
              onClick={onToggle}
              onDetailClick={setDetailAtom}
              size="sm"
            />
          ))}
        </div>
        {filtered.length === 0 && (
          <p className="text-center py-8 text-xs" style={{ color: "var(--text-muted)" }}>
            Atomが見つかりません
          </p>
        )}
      </div>
    </div>
  );
}
