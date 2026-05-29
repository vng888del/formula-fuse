"use client";
import type { Atom, FusedFormula, BondMatch } from "@/types";
import { ATOM_TYPE_CONFIG, getAtomAbbrev } from "@/lib/atomColors";

interface Props {
  selectedAtoms: Atom[];
  onRemove: (id: string) => void;
  formulaName: string;
  onFormulaNameChange: (name: string) => void;
  onFuse: () => void;
  loading: boolean;
  fused: FusedFormula | null;
  analysisComplete: boolean;
}

function getAtomPositions(count: number, radius: number): { x: number; y: number }[] {
  if (count === 0) return [];
  return Array.from({ length: count }, (_, i) => {
    const angle = (i / count) * 2 * Math.PI - Math.PI / 2;
    return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
  });
}

const RISK_COLOR: Record<string, string> = {
  green:  "#69f0ae",
  yellow: "#ffd54f",
  red:    "#ef5350",
  low:    "#69f0ae",
  medium: "#ffd54f",
  high:   "#ef5350",
};
const BOND_TYPE_ICON: Record<string, string> = {
  synergistic: "⊕",
  antagonistic: "⊗",
  substrate_enzyme: "→",
  fermentation: "⇌",
  process: "⚙",
  metabolic: "⟳",
};

function resolveBondLines(
  bonds: BondMatch[],
  atoms: Atom[],
  positions: { x: number; y: number }[],
): Array<{ x1: number; y1: number; x2: number; y2: number; bond: BondMatch }> {
  const lines: Array<{ x1: number; y1: number; x2: number; y2: number; bond: BondMatch }> = [];
  for (const bond of bonds) {
    const srcIdx = atoms.findIndex(
      (a) => a.atom_id === bond.source_atom || a.name_en === bond.source_atom || a.name_ja === bond.source_atom
    );
    const tgtIdx = atoms.findIndex(
      (a) => a.atom_id === bond.target_atom || a.name_en === bond.target_atom || a.name_ja === bond.target_atom
    );
    if (srcIdx === -1 || tgtIdx === -1) continue;
    lines.push({
      x1: 180 + positions[srcIdx].x,
      y1: 180 + positions[srcIdx].y,
      x2: 180 + positions[tgtIdx].x,
      y2: 180 + positions[tgtIdx].y,
      bond,
    });
  }
  return lines;
}

export function FusionCanvas({
  selectedAtoms, onRemove, formulaName, onFormulaNameChange, onFuse, loading, fused, analysisComplete,
}: Props) {
  const hasAtoms = selectedAtoms.length > 0;
  const canvasRadius = 140;
  const positions = getAtomPositions(selectedAtoms.length, canvasRadius);

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-primary)" }}>
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <h2 className="text-[10px] font-bold tracking-widest uppercase" style={{ color: "var(--text-secondary)" }}>
          Fusion Canvas
        </h2>
        <div className="flex items-center gap-2">
          {selectedAtoms.length > 0 && (
            <button
              onClick={() => selectedAtoms.forEach(a => onRemove(a.atom_id))}
              className="text-[10px] px-2 py-0.5 rounded transition-colors"
              style={{ color: "var(--text-muted)", border: "1px solid var(--border)" }}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Canvas area */}
      <div className="flex-1 relative overflow-hidden stars-bg">
        {/* Ambient glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0" style={{
            background: "radial-gradient(ellipse at center, rgba(79,195,247,0.03) 0%, transparent 70%)"
          }} />
        </div>

        {!hasAtoms ? (
          /* Empty state */
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <div
              className="w-24 h-24 rounded-full flex items-center justify-center"
              style={{
                background: "radial-gradient(circle, rgba(255,255,255,0.04) 0%, transparent 70%)",
                border: "1px dashed rgba(255,255,255,0.1)",
              }}
            >
              <svg className="w-8 h-8" style={{ color: "rgba(255,255,255,0.15)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 4v16m8-8H4" />
              </svg>
            </div>
            <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
              Drag atoms here to fuse
            </p>
          </div>
        ) : (
          /* Canvas with atoms and central orb */
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="relative" style={{ width: 360, height: 360 }}>
              {/* SVG connection lines */}
              <svg
                className="absolute inset-0 pointer-events-none"
                style={{ width: 360, height: 360, overflow: "visible" }}
              >
                {/* Bond match lines (colored by risk level) */}
                {fused && fused.bond_matches.length > 0
                  ? resolveBondLines(fused.bond_matches, selectedAtoms, positions).map((l, i) => {
                      const color = RISK_COLOR[l.bond.risk_level] || "#4fc3f7";
                      const mx = (l.x1 + l.x2) / 2;
                      const my = (l.y1 + l.y2) / 2;
                      return (
                        <g key={i}>
                          <line
                            x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2}
                            stroke={color}
                            strokeWidth={1.5}
                            strokeDasharray={l.bond.risk_level === "low" ? "none" : "5 3"}
                            opacity={0.55}
                          />
                          <text x={mx} y={my - 4} textAnchor="middle"
                            style={{ fontSize: 9, fill: color, opacity: 0.8, pointerEvents: "none" }}>
                            {BOND_TYPE_ICON[l.bond.bond_type] || "·"} {l.bond.confidence}
                          </text>
                        </g>
                      );
                    })
                  : /* Default spoke lines to center */
                    positions.map((pos, i) => {
                      const cfg = ATOM_TYPE_CONFIG[selectedAtoms[i].atom_type];
                      const x1 = 180 + pos.x;
                      const y1 = 180 + pos.y;
                      return (
                        <g key={i}>
                          <line
                            x1={x1} y1={y1} x2={180} y2={180}
                            stroke={cfg.color}
                            strokeWidth={1}
                            strokeDasharray="4 4"
                            style={{ animation: `line-glow ${1.5 + i * 0.3}s ease-in-out infinite alternate` }}
                            opacity={0.4}
                          />
                          <circle cx={x1} cy={y1} r={2} fill={cfg.color} opacity={0.6} />
                        </g>
                      );
                    })
                }
              </svg>

              {/* Atom nodes */}
              {selectedAtoms.map((atom, i) => {
                const pos = positions[i];
                const cfg = ATOM_TYPE_CONFIG[atom.atom_type];
                const abbrev = getAtomAbbrev(atom);
                return (
                  <div
                    key={atom.atom_id}
                    className="absolute flex flex-col items-center gap-1 animate-float"
                    style={{
                      left: 180 + pos.x - 28,
                      top: 180 + pos.y - 28,
                      animationDelay: `${i * 0.3}s`,
                    }}
                  >
                    <div
                      className="w-14 h-14 rounded-full flex items-center justify-center relative cursor-pointer group"
                      style={{
                        background: `radial-gradient(circle at 35% 35%, ${cfg.color}55, rgba(0,0,0,0.7))`,
                        border: `2px solid ${cfg.color}`,
                        boxShadow: `0 0 16px ${cfg.glow}, 0 0 32px ${cfg.glow.replace("0.5", "0.15")}`,
                      }}
                      onClick={() => onRemove(atom.atom_id)}
                    >
                      <span className="text-xs font-bold" style={{ color: cfg.color }}>
                        {abbrev}
                      </span>
                      <div className="absolute inset-0 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                        style={{ background: "rgba(0,0,0,0.6)" }}>
                        <span className="text-white text-sm">×</span>
                      </div>
                    </div>
                    <span className="text-[9px] leading-tight text-center w-16 truncate"
                      style={{ color: cfg.color }}>
                      {atom.name_ja}
                    </span>
                  </div>
                );
              })}

              {/* Central orb */}
              <div
                className="absolute flex flex-col items-center justify-center rounded-full animate-central-pulse"
                style={{
                  width: 130,
                  height: 130,
                  left: "50%",
                  top: "50%",
                  transform: "translate(-50%, -50%)",
                  background: analysisComplete
                    ? "radial-gradient(circle at 40% 35%, rgba(255,213,79,0.5), rgba(255,152,0,0.3) 50%, rgba(0,0,0,0.8))"
                    : "radial-gradient(circle at 40% 35%, rgba(79,195,247,0.2), rgba(108,58,219,0.15) 50%, rgba(0,0,0,0.8))",
                  border: `2px solid ${analysisComplete ? "rgba(255,213,79,0.5)" : "rgba(79,195,247,0.2)"}`,
                }}
              >
                {loading ? (
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-6 h-6 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "var(--blue)", borderTopColor: "transparent" }} />
                    <span className="text-[9px]" style={{ color: "var(--text-secondary)" }}>Analyzing...</span>
                  </div>
                ) : analysisComplete ? (
                  <div className="text-center px-2">
                    <div className="text-[9px] font-bold leading-tight" style={{ color: "rgba(255,213,79,0.9)" }}>
                      {formulaName || "Formula"}
                    </div>
                    <div className="text-[8px] mt-1 opacity-60" style={{ color: "var(--gold)" }}>FUSED</div>
                  </div>
                ) : (
                  <div className="text-center px-2">
                    <div className="text-[10px] leading-tight" style={{ color: "rgba(255,255,255,0.3)" }}>
                      {selectedAtoms.length} atoms
                    </div>
                    <div className="text-[8px] mt-1 opacity-40" style={{ color: "var(--text-muted)" }}>Ready to fuse</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bond legend strip */}
      {fused && fused.bond_matches.length > 0 && (
        <div className="shrink-0 px-4 py-2 overflow-x-auto flex gap-2" style={{ borderTop: "1px solid var(--border)", background: "rgba(13,13,36,0.6)", scrollbarWidth: "none" }}>
          {fused.bond_matches.slice(0, 5).map((b, i) => {
            const color = RISK_COLOR[b.risk_level] || "#4fc3f7";
            return (
              <div key={i} className="shrink-0 flex items-center gap-1.5 rounded-lg px-2 py-1"
                style={{ background: `${color}10`, border: `1px solid ${color}25` }}>
                <span style={{ fontSize: 10, color }}>{BOND_TYPE_ICON[b.bond_type] || "·"}</span>
                <div>
                  <p className="text-[8px] font-semibold leading-none" style={{ color }}>
                    {b.bond_type}
                  </p>
                  <p className="text-[8px] leading-none mt-0.5" style={{ color: "var(--text-muted)" }}>
                    {b.source_atom} × {b.target_atom}
                  </p>
                </div>
                <span className="text-[7px] px-1 rounded font-bold"
                  style={{ background: `${color}20`, color }}>
                  {b.confidence}
                </span>
              </div>
            );
          })}
          {fused.bond_matches.length > 5 && (
            <div className="shrink-0 flex items-center px-2">
              <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>+{fused.bond_matches.length - 5} bonds</span>
            </div>
          )}
        </div>
      )}

      {/* Ratio & Process Controls */}
      {selectedAtoms.length > 0 && (
        <div className="shrink-0 px-4 py-3" style={{ borderTop: "1px solid var(--border)", background: "rgba(13,13,36,0.8)" }}>
          <div className="flex items-center gap-1 mb-2">
            <span className="text-[9px] font-bold tracking-widest uppercase" style={{ color: "var(--text-secondary)" }}>
              Ratio & Process Controls
            </span>
          </div>
          <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${Math.min(selectedAtoms.length, 5)}, 1fr)` }}>
            {selectedAtoms.slice(0, 5).map((atom, i) => {
              const cfg = ATOM_TYPE_CONFIG[atom.atom_type];
              const ratio = Math.round(100 / selectedAtoms.length);
              return (
                <div key={atom.atom_id}>
                  <div className="flex justify-between mb-1">
                    <span className="text-[8px] truncate max-w-[60px]" style={{ color: cfg.color }}>{atom.name_ja}</span>
                    <span className="text-[8px]" style={{ color: "rgba(255,255,255,0.4)" }}>{ratio}%</span>
                  </div>
                  <div className="progress-track h-1 rounded-full">
                    <div
                      className="h-1 rounded-full transition-all"
                      style={{ width: `${ratio}%`, background: `linear-gradient(90deg, ${cfg.color}88, ${cfg.color})` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Formula name input */}
      <div className="shrink-0 px-4 py-2" style={{ borderTop: "1px solid var(--border)" }}>
        <input
          type="text"
          value={formulaName}
          onChange={(e) => onFormulaNameChange(e.target.value)}
          placeholder="Formula名を入力（任意）..."
          className="w-full text-xs outline-none rounded-lg px-3 py-1.5"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid var(--border)",
            color: "var(--text-primary)",
          }}
        />
      </div>

      {/* Fuse button */}
      <div className="shrink-0 px-4 pb-4">
        <button
          onClick={onFuse}
          disabled={selectedAtoms.length < 2 || loading}
          className="w-full py-3 rounded-xl font-bold text-sm tracking-wide btn-neon flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <circle cx={12} cy={12} r={3} strokeWidth={2} />
            <path strokeLinecap="round" strokeWidth={2} d="M12 2v2m0 16v2M2 12h2m16 0h2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41" />
          </svg>
          {loading ? "Analyzing..." : "FUSE FORMULA"}
          {!loading && <span className="text-lg leading-none">+</span>}
        </button>
        {selectedAtoms.length < 2 && (
          <p className="text-[9px] text-center mt-1.5" style={{ color: "var(--text-muted)" }}>
            2つ以上のAtomを選択してください
          </p>
        )}
      </div>
    </div>
  );
}
