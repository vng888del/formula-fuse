"use client";
import { useState, useEffect } from "react";
import type { BondRule, Atom } from "@/types";
import { ATOM_TYPE_CONFIG } from "@/lib/atomColors";
import { api } from "@/lib/api";

interface Props {
  atoms: Atom[];
  onClose: () => void;
}

// ── Layout ────────────────────────────────────────────────────────────────────

const CX = 300;
const CY = 260;
const R  = 185;   // pentagon radius
const NR = 46;    // node circle radius

const TYPE_ORDER = ["ingredient", "goal", "enzyme", "condition", "microbe"] as const;

type TypeKey = typeof TYPE_ORDER[number];

const TYPE_POS: Record<TypeKey, { x: number; y: number }> = (() => {
  const out = {} as Record<TypeKey, { x: number; y: number }>;
  TYPE_ORDER.forEach((type, i) => {
    const angle = -Math.PI / 2 + i * (2 * Math.PI / 5);
    out[type] = { x: CX + Math.cos(angle) * R, y: CY + Math.sin(angle) * R };
  });
  return out;
})();

const CONF_WIDTH: Record<string, number> = { high: 3.5, medium: 2, low: 1.2 };

const RISK_DASH: Record<string, string> = {
  green:  "none",
  yellow: "6 3",
  red:    "3 3",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Edge key — canonical (sorted) so A→B == B→A for bidirectional check. */
function edgeKey(s: string, t: string): string {
  return s < t ? `${s}::${t}` : `${t}::${s}`;
}

/** Quadratic bezier control point — offset perpendicular to the midpoint. */
function controlPoint(
  x1: number, y1: number, x2: number, y2: number,
  offset: number
): { cx: number; cy: number } {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy) || 1;
  return { cx: mx + (-dy / len) * offset, cy: my + (dx / len) * offset };
}

/** Point on node circle edge towards (tx, ty). */
function nodeEdgePoint(
  nx: number, ny: number, tx: number, ty: number
): { x: number; y: number } {
  const dx = tx - nx;
  const dy = ty - ny;
  const len = Math.hypot(dx, dy) || 1;
  return { x: nx + (dx / len) * NR, y: ny + (dy / len) * NR };
}

// ── Main component ────────────────────────────────────────────────────────────

export function BondGraphPanel({ atoms, onClose }: Props) {
  const [bondRules, setBondRules] = useState<BondRule[]>([]);
  const [hovered, setHovered] = useState<{ key: string; rules: BondRule[] } | null>(null);
  const [selectedType, setSelectedType] = useState<TypeKey | null>(null);

  useEffect(() => {
    api.atoms.bondRules().then(setBondRules).catch(() => {});
  }, []);

  // Group rules by source→target pair
  const edgeGroups = new Map<string, BondRule[]>();
  for (const r of bondRules) {
    const k = `${r.source_atom_type}::${r.target_atom_type}`;
    if (!edgeGroups.has(k)) edgeGroups.set(k, []);
    edgeGroups.get(k)!.push(r);
  }

  // Count atoms per type
  const atomCount: Record<string, number> = {};
  for (const a of atoms) atomCount[a.atom_type] = (atomCount[a.atom_type] ?? 0) + 1;

  // Bidirectional pairs
  const bidir = new Set<string>();
  for (const k of edgeGroups.keys()) {
    const [s, t] = k.split("::");
    const rev = `${t}::${s}`;
    if (edgeGroups.has(rev) && s !== t) bidir.add(edgeKey(s, t));
  }

  // Atoms filtered by selected type
  const filteredAtoms = selectedType
    ? atoms.filter((a) => a.atom_type === selectedType)
    : [];

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-primary)" }}>
      {/* Header */}
      <div className="shrink-0 px-6 py-3 flex items-center justify-between"
        style={{ borderBottom: "1px solid var(--border)", background: "rgba(13,13,36,0.8)" }}>
        <div className="flex items-center gap-2">
          <span style={{ color: "var(--blue)" }}>🕸</span>
          <h2 className="text-[10px] font-bold tracking-widest uppercase" style={{ color: "var(--text-secondary)" }}>
            Bond Graph
          </h2>
          <span className="text-[9px] px-2 py-0.5 rounded-full"
            style={{ background: "rgba(79,195,247,0.1)", color: "var(--blue)", border: "1px solid rgba(79,195,247,0.2)" }}>
            {bondRules.length} rules
          </span>
        </div>
        <button onClick={onClose} className="text-xs px-2 py-0.5 rounded transition-colors"
          style={{ color: "var(--text-muted)", border: "1px solid var(--border)" }}>
          ← Studio
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Graph area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 flex items-center justify-center">
            <svg width={600} height={520} viewBox="0 0 600 520" className="overflow-visible">
              {/* Defs: arrowheads */}
              <defs>
                {["green", "yellow", "red"].map((risk) => (
                  <marker key={risk} id={`arrow-${risk}`} markerWidth={8} markerHeight={8}
                    refX={6} refY={3} orient="auto">
                    <path d="M0,0 L0,6 L8,3 z"
                      fill={risk === "green" ? "#69f0ae" : risk === "yellow" ? "#ffd54f" : "#ef5350"}
                      opacity={0.7} />
                  </marker>
                ))}
              </defs>

              {/* Edges */}
              {Array.from(edgeGroups.entries()).map(([key, rules]) => {
                const [srcType, tgtType] = key.split("::");
                if (!(srcType in TYPE_POS) || !(tgtType in TYPE_POS)) return null;

                const sp = TYPE_POS[srcType as TypeKey];
                const tp = TYPE_POS[tgtType as TypeKey];
                const cfg = ATOM_TYPE_CONFIG[srcType as TypeKey] ??
                            (ATOM_TYPE_CONFIG as Record<string, typeof ATOM_TYPE_CONFIG[TypeKey]>)[srcType];
                const riskLevel = rules[0]?.risk_level ?? "yellow";
                const color = riskLevel === "green" ? "#69f0ae" : riskLevel === "yellow" ? "#ffd54f" : "#ef5350";

                const isSelf = srcType === tgtType;
                const isHovered = hovered?.key === key;

                let pathD: string;
                let labelX: number;
                let labelY: number;

                if (isSelf) {
                  // Loop above the node
                  const lx = sp.x;
                  const ly = sp.y - NR;
                  pathD = `M ${lx - 30},${ly} C ${lx - 70},${ly - 80} ${lx + 70},${ly - 80} ${lx + 30},${ly}`;
                  labelX = lx;
                  labelY = ly - 68;
                } else {
                  // Check if reverse direction also exists → offset curve
                  const isBidir = bidir.has(edgeKey(srcType, tgtType));
                  const offsetDir = srcType < tgtType ? 1 : -1;
                  const offsetAmt = isBidir ? 55 : 0;

                  const ep0 = nodeEdgePoint(sp.x, sp.y, tp.x, tp.y);
                  const ep1 = nodeEdgePoint(tp.x, tp.y, sp.x, sp.y);
                  const { cx, cy } = controlPoint(ep0.x, ep0.y, ep1.x, ep1.y, offsetAmt * offsetDir);
                  pathD = `M ${ep0.x},${ep0.y} Q ${cx},${cy} ${ep1.x},${ep1.y}`;
                  labelX = (ep0.x + 2 * cx + ep1.x) / 4;
                  labelY = (ep0.y + 2 * cy + ep1.y) / 4;
                }

                const strokeW = CONF_WIDTH[rules[0]?.confidence ?? "medium"] * (isHovered ? 2 : 1);

                return (
                  <g key={key}
                    onMouseEnter={() => setHovered({ key, rules })}
                    onMouseLeave={() => setHovered(null)}
                    style={{ cursor: "pointer" }}>
                    {/* Wide invisible hit area */}
                    <path d={pathD} fill="none" stroke="transparent" strokeWidth={16} />
                    {/* Visible path */}
                    <path
                      d={pathD}
                      fill="none"
                      stroke={isHovered ? "white" : color}
                      strokeWidth={strokeW}
                      strokeDasharray={RISK_DASH[riskLevel]}
                      opacity={isHovered ? 1 : 0.55}
                      markerEnd={isSelf ? undefined : `url(#arrow-${riskLevel})`}
                      style={{ transition: "opacity 0.15s, stroke 0.15s" }}
                    />
                    {/* Count badge */}
                    {rules.length > 1 && (
                      <>
                        <circle cx={labelX} cy={labelY} r={9}
                          fill="rgba(13,13,36,0.9)"
                          stroke={color} strokeWidth={1} />
                        <text x={labelX} y={labelY + 3.5} textAnchor="middle"
                          style={{ fontSize: 9, fill: color, fontWeight: 700, pointerEvents: "none" }}>
                          {rules.length}
                        </text>
                      </>
                    )}
                  </g>
                );
              })}

              {/* Nodes */}
              {TYPE_ORDER.map((type) => {
                const pos = TYPE_POS[type];
                const cfg = ATOM_TYPE_CONFIG[type];
                const n = atomCount[type] ?? 0;
                const ruleCount = Array.from(edgeGroups.entries())
                  .filter(([k]) => k.startsWith(`${type}::`) || k.endsWith(`::${type}`))
                  .reduce((s, [, r]) => s + r.length, 0);
                const isSelected = selectedType === type;

                return (
                  <g key={type} style={{ cursor: "pointer" }}
                    onClick={() => setSelectedType(isSelected ? null : type)}>
                    {/* Glow ring when selected */}
                    {isSelected && (
                      <circle cx={pos.x} cy={pos.y} r={NR + 8}
                        fill="none" stroke={cfg.color} strokeWidth={2} opacity={0.4} />
                    )}
                    {/* Node circle */}
                    <circle
                      cx={pos.x} cy={pos.y} r={NR}
                      fill={isSelected ? `${cfg.color}22` : "rgba(13,13,36,0.9)"}
                      stroke={cfg.color}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                      opacity={0.95}
                    />
                    {/* Atom count */}
                    <text x={pos.x} y={pos.y - 6} textAnchor="middle"
                      style={{ fontSize: 18, fontWeight: 800, fill: cfg.color, pointerEvents: "none" }}>
                      {n}
                    </text>
                    {/* Type label */}
                    <text x={pos.x} y={pos.y + 10} textAnchor="middle"
                      style={{ fontSize: 9, fill: cfg.color, opacity: 0.8, pointerEvents: "none" }}>
                      {cfg.label}
                    </text>
                    {/* Rule count */}
                    <text x={pos.x} y={pos.y + 22} textAnchor="middle"
                      style={{ fontSize: 8, fill: "rgba(255,255,255,0.3)", pointerEvents: "none" }}>
                      {ruleCount} rules
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Legend */}
          <div className="shrink-0 px-6 pb-4 flex items-center gap-6 justify-center">
            <div className="flex items-center gap-1.5">
              <div className="w-6 h-0.5 rounded" style={{ background: "#69f0ae" }} />
              <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>Green（低リスク）</span>
            </div>
            <div className="flex items-center gap-1.5">
              <svg width={24} height={4}><line x1={0} y1={2} x2={24} y2={2} stroke="#ffd54f" strokeWidth={2} strokeDasharray="5 3" /></svg>
              <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>Yellow（要注意）</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[9px]" style={{ color: "rgba(255,255,255,0.3)" }}>太さ = confidence (high/medium/low)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[9px] px-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)", color: "var(--text-muted)" }}>数字 = ルール数</span>
            </div>
          </div>
        </div>

        {/* Side panel: hover detail OR selected type atom list */}
        <div className="w-72 shrink-0 overflow-y-auto"
          style={{ borderLeft: "1px solid var(--border)", background: "rgba(13,13,36,0.6)" }}>
          {hovered ? (
            <EdgeDetail rules={hovered.rules} />
          ) : selectedType ? (
            <TypeAtomList type={selectedType} atoms={filteredAtoms} />
          ) : (
            <GraphHelp />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Side panel sub-components ─────────────────────────────────────────────────

function GraphHelp() {
  return (
    <div className="px-4 py-6 flex flex-col gap-3">
      <p className="text-[9px] font-bold tracking-widest uppercase" style={{ color: "var(--text-muted)" }}>
        操作方法
      </p>
      <div className="space-y-2">
        {[
          ["エッジにホバー", "Bond Rule の詳細を表示"],
          ["ノードをクリック", "そのタイプの Atom 一覧を表示"],
          ["エッジの太さ", "confidence（high=太、low=細）"],
          ["エッジの点線", "risk_level（solid=green、dashed=yellow）"],
          ["数字バッジ", "そのペア間の Bond Rule 数"],
        ].map(([k, v]) => (
          <div key={k}>
            <p className="text-[10px] font-semibold" style={{ color: "rgba(255,255,255,0.6)" }}>{k}</p>
            <p className="text-[9px]" style={{ color: "var(--text-muted)" }}>{v}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function EdgeDetail({ rules }: { rules: BondRule[] }) {
  const srcCfg = ATOM_TYPE_CONFIG[rules[0].source_atom_type as TypeKey];
  const tgtCfg = ATOM_TYPE_CONFIG[rules[0].target_atom_type as TypeKey];
  return (
    <div className="px-4 py-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-bold" style={{ color: srcCfg?.color ?? "var(--blue)" }}>
          {ATOM_TYPE_CONFIG[rules[0].source_atom_type as TypeKey]?.label ?? rules[0].source_atom_type}
        </span>
        <span style={{ color: "var(--text-muted)" }}>→</span>
        <span className="text-[10px] font-bold" style={{ color: tgtCfg?.color ?? "var(--blue)" }}>
          {ATOM_TYPE_CONFIG[rules[0].target_atom_type as TypeKey]?.label ?? rules[0].target_atom_type}
        </span>
        <span className="text-[8px] px-1.5 rounded-full ml-auto"
          style={{ background: "rgba(79,195,247,0.1)", color: "var(--blue)", border: "1px solid rgba(79,195,247,0.2)" }}>
          {rules.length} ルール
        </span>
      </div>

      {rules.map((r) => {
        const riskColor = r.risk_level === "green" ? "#69f0ae" : r.risk_level === "yellow" ? "#ffd54f" : "#ef5350";
        return (
          <div key={r.bond_rule_id} className="rounded-xl p-3 space-y-2"
            style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${riskColor}20` }}>
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded"
                style={{ background: `${riskColor}15`, color: riskColor }}>
                {r.bond_type}
              </span>
              <span className="text-[8px] px-1 rounded"
                style={{ background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.4)" }}>
                {r.confidence}
              </span>
              <span className="text-[8px] px-1 rounded"
                style={{ background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.4)" }}>
                {r.risk_level}
              </span>
            </div>
            <p className="text-[9px] leading-relaxed" style={{ color: "rgba(255,255,255,0.55)" }}>
              {r.explanation}
            </p>
            {r.source_required_tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                <span className="text-[8px]" style={{ color: "var(--text-muted)" }}>要タグ:</span>
                {r.source_required_tags.concat(r.target_required_tags).map((tag) => (
                  <span key={tag} className="text-[7px] px-1 rounded"
                    style={{ background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.35)" }}>
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function TypeAtomList({ type, atoms }: { type: TypeKey; atoms: Atom[] }) {
  const cfg = ATOM_TYPE_CONFIG[type];
  return (
    <div className="px-4 py-4">
      <p className="text-[9px] font-bold tracking-widest uppercase mb-3" style={{ color: "var(--text-muted)" }}>
        {cfg.label} — {atoms.length} atoms
      </p>
      <div className="space-y-1.5">
        {atoms.map((a) => (
          <div key={a.atom_id} className="rounded-lg px-3 py-2 flex items-center justify-between"
            style={{ background: `${cfg.color}08`, border: `1px solid ${cfg.color}20` }}>
            <div>
              <p className="text-[10px] font-semibold" style={{ color: cfg.color }}>{a.name_ja}</p>
              <p className="text-[8px]" style={{ color: "var(--text-muted)" }}>{a.name_en}</p>
            </div>
            <div className="flex flex-col items-end gap-0.5">
              {a.gras && (
                <span className="text-[7px] px-1 rounded font-bold"
                  style={{ background: "rgba(105,240,174,0.1)", color: "#69f0ae" }}>
                  {a.gras.status}
                </span>
              )}
              {a.pubmed_evidence && a.pubmed_evidence.length > 0 && (
                <span className="text-[7px]" style={{ color: "rgba(79,195,247,0.7)" }}>
                  {a.pubmed_evidence.length}文献
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
