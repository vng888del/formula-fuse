"use client";
import type { Atom } from "@/types";
import { ATOM_TYPE_CONFIG } from "@/lib/atomColors";

interface Props {
  atoms: Atom[];
  onClose: () => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function countBy<T>(arr: T[], key: (v: T) => string): Record<string, number> {
  const out: Record<string, number> = {};
  for (const v of arr) {
    const k = key(v);
    out[k] = (out[k] ?? 0) + 1;
  }
  return Object.fromEntries(Object.entries(out).sort((a, b) => b[1] - a[1]));
}

function evLevel(n: number): string {
  if (n === 0) return "E0";
  if (n <= 2)  return "E1";
  if (n <= 5)  return "E2";
  if (n <= 10) return "E3";
  if (n <= 20) return "E4";
  return "E5";
}

const EV_COLOR: Record<string, string> = {
  E0: "rgba(255,255,255,0.15)",
  E1: "#4fc3f7",
  E2: "#69f0ae",
  E3: "#ffd54f",
  E4: "#f48fb1",
  E5: "#ce93d8",
};

const GRAS_COLOR: Record<string, string> = {
  GRAS: "#69f0ae",
  NDI: "#4fc3f7",
  food_additive: "#ffd54f",
  unknown: "rgba(255,255,255,0.25)",
};

const GRAS_LABEL: Record<string, string> = {
  GRAS: "FDA GRAS",
  NDI: "NDI",
  food_additive: "食品添加物",
  unknown: "未確認",
};

const TIER_COLOR: Record<string, string> = {
  low: "#69f0ae",
  medium: "#4fc3f7",
  high: "#ffd54f",
  very_high: "#ef5350",
};

const ENRICH_FIELDS: Array<{ key: keyof Atom; label: string; phase: string; color: string }> = [
  { key: "compound",          label: "PubChem 化合物",   phase: "Ph1", color: "#4fc3f7" },
  { key: "usda",              label: "USDA 栄養",        phase: "Ph1", color: "#80deea" },
  { key: "uniprot",           label: "UniProt 酵素",     phase: "Ph2", color: "#ce93d8" },
  { key: "pubmed_evidence",   label: "PubMed 文献",      phase: "Ph2", color: "#b39ddb" },
  { key: "gras",              label: "FDA GRAS",         phase: "Ph3", color: "#69f0ae" },
  { key: "supplier_info",     label: "サプライヤー",     phase: "Ph4", color: "#ffd54f" },
  { key: "patent_landscape",  label: "Lens 特許",        phase: "Ph4", color: "#ffcc80" },
  { key: "market_trends",     label: "Google Trends",   phase: "Ph5", color: "#f48fb1" },
  { key: "existing_products", label: "Open Food Facts", phase: "Ph5", color: "#ef9a9a" },
];

const ATOM_TYPE_ORDER = ["ingredient", "microbe", "enzyme", "condition", "goal", "process"] as const;

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({ value, label, color }: { value: number | string; label: string; color: string }) {
  return (
    <div className="rounded-xl p-3 flex flex-col gap-1"
      style={{ background: `${color}08`, border: `1px solid ${color}20` }}>
      <span className="text-2xl font-bold tabular-nums" style={{ color }}>{value}</span>
      <span className="text-[9px] font-semibold tracking-wide uppercase" style={{ color: "var(--text-muted)" }}>{label}</span>
    </div>
  );
}

function Bar({ pct, color, height = 6 }: { pct: number; color: string; height?: number }) {
  return (
    <div className="rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)", height }}>
      <div className="rounded-full transition-all duration-700"
        style={{ width: `${Math.max(pct, pct > 0 ? 2 : 0)}%`, height, background: color }} />
    </div>
  );
}

function SectionHeader({ label }: { label: string }) {
  return (
    <p className="text-[9px] font-bold tracking-widest uppercase mb-3" style={{ color: "var(--text-muted)" }}>
      {label}
    </p>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export function AnalyticsPanel({ atoms, onClose }: Props) {
  const total = atoms.length;

  // Atom type distribution
  const byType = countBy(atoms, (a) => a.atom_type);

  // Enrichment coverage
  const enrichCounts = ENRICH_FIELDS.map((f) => {
    const n = atoms.filter((a) => {
      const v = a[f.key];
      return Array.isArray(v) ? v.length > 0 : !!v;
    }).length;
    return { ...f, n, pct: Math.round((n / total) * 100) };
  });

  // GRAS status breakdown (ingredients+enzymes+microbes only)
  const grasAtoms = atoms.filter((a) => a.gras);
  const byGras = countBy(grasAtoms, (a) => a.gras!.status);

  // Evidence level distribution
  const byEv = countBy(atoms, (a) => evLevel(a.pubmed_evidence?.length ?? 0));

  // Supplier tier
  const supplierAtoms = atoms.filter((a) => a.supplier_info?.price_tier);
  const byTier = countBy(supplierAtoms, (a) => a.supplier_info!.price_tier!);

  // Top categories
  const topCats = Object.entries(countBy(atoms, (a) => a.category))
    .slice(0, 8);

  // Enriched atom count
  const fullyEnriched = atoms.filter((a) =>
    a.gras && a.pubmed_evidence && a.pubmed_evidence.length > 0
  ).length;

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-primary)" }}>
      {/* Header */}
      <div className="shrink-0 px-6 py-3 flex items-center justify-between"
        style={{ borderBottom: "1px solid var(--border)", background: "rgba(13,13,36,0.8)" }}>
        <div className="flex items-center gap-2">
          <span style={{ color: "var(--blue)" }}>📊</span>
          <h2 className="text-[10px] font-bold tracking-widest uppercase" style={{ color: "var(--text-secondary)" }}>
            Analytics
          </h2>
        </div>
        <button onClick={onClose} className="text-xs px-2 py-0.5 rounded transition-colors"
          style={{ color: "var(--text-muted)", border: "1px solid var(--border)" }}>
          ← Studio
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-5 grid gap-6">

          {/* ── Stat cards ── */}
          <div className="grid grid-cols-4 gap-3">
            <StatCard value={total} label="Total Atoms" color="var(--blue)" />
            <StatCard value={fullyEnriched} label="GRAS + Evidence" color="var(--green)" />
            <StatCard value={supplierAtoms.length} label="調達情報あり" color="var(--gold)" />
            <StatCard
              value={`${Math.round((enrichCounts.filter(f => f.key === "gras")[0]?.pct ?? 0))}%`}
              label="GRAS カバー率"
              color="#ce93d8"
            />
          </div>

          <div className="grid grid-cols-2 gap-6">

            {/* ── Atom type distribution ── */}
            <div className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
              <SectionHeader label="Atom タイプ分布" />
              <div className="space-y-2.5">
                {ATOM_TYPE_ORDER.map((type) => {
                  const cfg = ATOM_TYPE_CONFIG[type];
                  const n = byType[type] ?? 0;
                  if (n === 0) return null;
                  return (
                    <div key={type}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-medium" style={{ color: cfg.color }}>{cfg.label}</span>
                        <span className="text-[9px] tabular-nums" style={{ color: "var(--text-muted)" }}>
                          {n} / {total}
                        </span>
                      </div>
                      <Bar pct={(n / total) * 100} color={cfg.color} />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ── GRAS status ── */}
            <div className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
              <SectionHeader label="GRAS ステータス" />
              <div className="space-y-2.5">
                {Object.entries(byGras).map(([status, n]) => {
                  const color = GRAS_COLOR[status] ?? "rgba(255,255,255,0.3)";
                  return (
                    <div key={status}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-medium" style={{ color }}>
                          {GRAS_LABEL[status] ?? status}
                        </span>
                        <span className="text-[9px] tabular-nums" style={{ color: "var(--text-muted)" }}>{n}</span>
                      </div>
                      <Bar pct={(n / grasAtoms.length) * 100} color={color} />
                    </div>
                  );
                })}
                {grasAtoms.length < total && (
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px]" style={{ color: "rgba(255,255,255,0.2)" }}>未評価</span>
                      <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>{total - grasAtoms.length}</span>
                    </div>
                    <Bar pct={((total - grasAtoms.length) / total) * 100} color="rgba(255,255,255,0.08)" />
                  </div>
                )}
              </div>
            </div>

            {/* ── Evidence level ── */}
            <div className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
              <SectionHeader label="エビデンスレベル（PubMed）" />
              <div className="space-y-2.5">
                {["E5", "E4", "E3", "E2", "E1", "E0"].map((lv) => {
                  const n = byEv[lv] ?? 0;
                  if (n === 0) return null;
                  const color = EV_COLOR[lv];
                  const labels: Record<string, string> = {
                    E5: "E5 20件超", E4: "E4 11–20件", E3: "E3 6–10件",
                    E2: "E2 3–5件",  E1: "E1 1–2件",  E0: "E0 なし",
                  };
                  return (
                    <div key={lv}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-medium" style={{ color }}>{labels[lv]}</span>
                        <span className="text-[9px] tabular-nums" style={{ color: "var(--text-muted)" }}>{n}</span>
                      </div>
                      <Bar pct={(n / total) * 100} color={color} />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ── Supplier tier ── */}
            <div className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
              <SectionHeader label="サプライヤー調達コスト" />
              {supplierAtoms.length === 0 ? (
                <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>データなし</p>
              ) : (
                <div className="space-y-2.5">
                  {(["low", "medium", "high", "very_high"] as const).map((tier) => {
                    const n = byTier[tier] ?? 0;
                    if (n === 0) return null;
                    const labels = { low: "Low（低コスト）", medium: "Medium", high: "High", very_high: "Very High（高コスト）" };
                    return (
                      <div key={tier}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[10px] font-medium" style={{ color: TIER_COLOR[tier] }}>{labels[tier]}</span>
                          <span className="text-[9px] tabular-nums" style={{ color: "var(--text-muted)" }}>{n}</span>
                        </div>
                        <Bar pct={(n / supplierAtoms.length) * 100} color={TIER_COLOR[tier]} />
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* ── Phase 1–5 enrichment coverage ── */}
          <div className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
            <SectionHeader label="Phase 1–5 エンリッチメント カバレッジ" />
            <div className="grid grid-cols-2 gap-x-8 gap-y-2.5">
              {enrichCounts.map((f) => (
                <div key={String(f.key)}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[7px] px-1 rounded font-bold"
                        style={{ background: `${f.color}20`, color: f.color, border: `1px solid ${f.color}30` }}>
                        {f.phase}
                      </span>
                      <span className="text-[10px]" style={{ color: "rgba(255,255,255,0.6)" }}>{f.label}</span>
                    </div>
                    <span className="text-[9px] tabular-nums" style={{ color: f.pct === 0 ? "#ef5350" : f.pct === 100 ? "#69f0ae" : "var(--text-muted)" }}>
                      {f.n}/{total}
                    </span>
                  </div>
                  <Bar pct={f.pct} color={f.pct === 0 ? "rgba(239,83,80,0.3)" : f.color} height={5} />
                </div>
              ))}
            </div>
          </div>

          {/* ── Top categories ── */}
          <div className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
            <SectionHeader label="カテゴリ上位" />
            <div className="flex flex-wrap gap-1.5">
              {topCats.map(([cat, n]) => (
                <div key={cat} className="flex items-center gap-1 rounded-lg px-2 py-1"
                  style={{ background: "rgba(79,195,247,0.06)", border: "1px solid rgba(79,195,247,0.15)" }}>
                  <span className="text-[10px]" style={{ color: "var(--blue)" }}>{cat}</span>
                  <span className="text-[9px] font-bold" style={{ color: "rgba(79,195,247,0.5)" }}>{n}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
