"use client";
import type { Atom } from "@/types";
import { ATOM_TYPE_CONFIG } from "@/lib/atomColors";

interface UsdaData {
  fdc_id?: number;
  description?: string;
  food_category?: string;
  data_type?: string;
  usda_url?: string;
  nutrients?: {
    energy_kcal?: number;
    protein_g?: number;
    fat_g?: number;
    carb_g?: number;
    fiber_g?: number;
    calcium_mg?: number;
    iron_mg?: number;
  };
}

interface Props {
  atom: Atom;
  onClose: () => void;
}

const TREND_ICON: Record<string, string> = {
  rising: "↑",
  stable: "→",
  declining: "↓",
};
const TREND_COLOR: Record<string, string> = {
  rising: "#69f0ae",
  stable: "#ffd54f",
  declining: "#ef5350",
};

export function AtomDetailPanel({ atom, onClose }: Props) {
  const cfg = ATOM_TYPE_CONFIG[atom.atom_type];

  return (
    <div
      className="flex flex-col h-full overflow-y-auto"
      style={{ background: "var(--bg-secondary)", fontSize: 11 }}
    >
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center justify-between shrink-0"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2">
          <span style={{ color: cfg.color }}>⬡</span>
          <div>
            <p className="font-bold text-xs" style={{ color: cfg.color }}>{atom.name_ja}</p>
            <p className="text-[9px]" style={{ color: "var(--text-muted)" }}>{atom.name_en}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="w-6 h-6 flex items-center justify-center rounded-full transition-colors"
          style={{ color: "var(--text-muted)", background: "rgba(255,255,255,0.05)" }}
        >
          ×
        </button>
      </div>

      <div className="flex-1 px-4 py-3 space-y-4">

        {/* Compound data */}
        {atom.compound && (
          <Section label="化合物データ" icon="⚗️">
            <Row k="分子式" v={atom.compound.molecular_formula} />
            <Row k="分子量" v={atom.compound.molecular_weight != null ? `${atom.compound.molecular_weight} Da` : undefined} />
            {atom.compound.pubchem_url && (
              <a
                href={atom.compound.pubchem_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[10px] underline"
                style={{ color: "var(--blue)" }}
              >
                PubChem →
              </a>
            )}
          </Section>
        )}

        {/* USDA Nutritional data */}
        {atom.usda && (() => {
          const usda = atom.usda as UsdaData;
          const n = usda.nutrients;
          const rows: [string, number | undefined, string][] = [
            ["エネルギー", n?.energy_kcal, "kcal"],
            ["タンパク質", n?.protein_g, "g"],
            ["脂質", n?.fat_g, "g"],
            ["炭水化物", n?.carb_g, "g"],
            ["カルシウム", n?.calcium_mg, "mg"],
            ["鉄分", n?.iron_mg, "mg"],
          ];
          return (
            <Section label="USDA 栄養データ" icon="🌾">
              <Row k="食品名" v={usda.description} />
              <Row k="カテゴリ" v={usda.food_category} />
              <Row k="データ種別" v={usda.data_type} />
              {n && (
                <div className="grid grid-cols-2 gap-1 mt-1">
                  {rows.filter(([, v]) => v != null).map(([label, val, unit]) => (
                    <div key={label} className="rounded p-1 text-center" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
                      <p className="text-[8px]" style={{ color: "var(--text-muted)" }}>{label}</p>
                      <p className="text-[10px] font-bold" style={{ color: "rgba(255,255,255,0.75)" }}>
                        {Number(val).toFixed(1)}
                        <span className="text-[8px] ml-0.5" style={{ color: "var(--text-muted)" }}>{unit}</span>
                      </p>
                    </div>
                  ))}
                </div>
              )}
              {usda.usda_url && (
                <a href={usda.usda_url} target="_blank" rel="noopener noreferrer"
                  className="text-[10px] underline" style={{ color: "var(--blue)" }}>FoodData Central →</a>
              )}
            </Section>
          );
        })()}

        {/* UniProt / enzyme data */}
        {atom.uniprot && (
          <Section label="UniProt / 酵素情報" icon="🧬">
            {atom.uniprot.ec_numbers && atom.uniprot.ec_numbers.length > 0 && (
              <Row k="EC番号" v={atom.uniprot.ec_numbers.join(", ")} />
            )}
            {atom.uniprot.organism && <Row k="生物種" v={atom.uniprot.organism} />}
            {atom.uniprot.function_comment && (
              <p className="text-[10px] leading-relaxed" style={{ color: "rgba(255,255,255,0.55)" }}>
                {atom.uniprot.function_comment.slice(0, 200)}{atom.uniprot.function_comment.length > 200 ? "…" : ""}
              </p>
            )}
            {atom.uniprot.catalytic_activity && atom.uniprot.catalytic_activity.length > 0 && (
              <div>
                <p className="text-[9px] font-semibold mb-0.5" style={{ color: "var(--text-muted)" }}>触媒反応</p>
                <p className="text-[10px] leading-relaxed" style={{ color: "rgba(255,255,255,0.5)" }}>
                  {atom.uniprot.catalytic_activity[0].slice(0, 150)}{(atom.uniprot.catalytic_activity[0]?.length ?? 0) > 150 ? "…" : ""}
                </p>
              </div>
            )}
          </Section>
        )}

        {/* GRAS / Safety */}
        {atom.gras && (
          <Section label="安全性・規制" icon="🛡️">
            <Row k="FDA GRAS" v={atom.gras.status} />
            {atom.gras.basis && <Row k="根拠" v={atom.gras.basis} />}
            {atom.gras.jp_status && <Row k="日本規制" v={atom.gras.jp_status} />}
            {atom.gras.notes && (
              <p className="text-[10px] leading-relaxed" style={{ color: "rgba(255,152,0,0.8)" }}>
                {atom.gras.notes}
              </p>
            )}
          </Section>
        )}

        {/* PubMed evidence */}
        {atom.pubmed_evidence && atom.pubmed_evidence.length > 0 && (
          <Section label={`PubMed 文献 (${atom.pubmed_evidence.length}件)`} icon="📄">
            <div className="space-y-2">
              {atom.pubmed_evidence.slice(0, 3).map((p) => (
                <div key={p.pmid} className="rounded-lg p-2" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
                  <a
                    href={p.pubmed_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] font-medium leading-tight underline"
                    style={{ color: "var(--blue)" }}
                  >
                    {p.title.slice(0, 80)}{p.title.length > 80 ? "…" : ""}
                  </a>
                  <p className="text-[9px] mt-0.5" style={{ color: "var(--text-muted)" }}>
                    {p.journal} · {p.year}
                  </p>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Supplier info */}
        {atom.supplier_info && (
          <Section label="サプライヤー情報" icon="🏭">
            <Row k="調達コスト" v={atom.supplier_info.price_tier} />
            {atom.supplier_info.oem_forms.length > 0 && (
              <Row k="OEM剤形" v={atom.supplier_info.oem_forms.join(", ")} />
            )}
            {atom.supplier_info.major_suppliers.length > 0 && (
              <Row k="主要サプライヤー" v={atom.supplier_info.major_suppliers.slice(0, 2).join(", ")} />
            )}
            {atom.supplier_info.japan_suppliers.length > 0 && (
              <Row k="日本代理店" v={atom.supplier_info.japan_suppliers.slice(0, 2).join(", ")} />
            )}
            {atom.supplier_info.certifications && atom.supplier_info.certifications.length > 0 && (
              <Row k="認証" v={atom.supplier_info.certifications.join(", ")} />
            )}
          </Section>
        )}

        {/* Patent landscape */}
        {atom.patent_landscape && (
          <Section label="特許ランドスケープ" icon="🔒">
            <Row k="総件数" v={`${atom.patent_landscape.total_count.toLocaleString()}件`} />
            <Row k="JP" v={`${atom.patent_landscape.jp_count}件`} />
            <Row k="US" v={`${atom.patent_landscape.us_count}件`} />
          </Section>
        )}

        {/* Market trends */}
        {atom.market_trends && (
          <Section label="市場トレンド" icon="📈">
            <div className="flex items-center gap-1.5 mb-1">
              <span
                className="text-xs font-bold"
                style={{ color: TREND_COLOR[atom.market_trends.trend_direction] || "var(--text-primary)" }}
              >
                {TREND_ICON[atom.market_trends.trend_direction]} {atom.market_trends.trend_direction}
              </span>
              <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>
                ({atom.market_trends.keyword})
              </span>
            </div>
            <div className="grid grid-cols-3 gap-1">
              {[
                { label: "JP", val: atom.market_trends.avg_interest_jp },
                { label: "US", val: atom.market_trends.avg_interest_us },
                { label: "WW", val: atom.market_trends.avg_interest_ww },
              ].map(({ label, val }) => (
                <div key={label} className="rounded p-1.5 text-center" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
                  <p className="text-[8px]" style={{ color: "var(--text-muted)" }}>{label}</p>
                  <p className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>{val}</p>
                  <div className="mt-0.5 h-0.5 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
                    <div className="h-0.5 rounded-full" style={{ width: `${val}%`, background: "var(--blue)" }} />
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Existing products */}
        {atom.existing_products && atom.existing_products.total_count > 0 && (
          <Section label="既存製品 (Open Food Facts)" icon="🛒">
            <Row k="製品数" v={`${atom.existing_products.total_count.toLocaleString()}件`} />
            {atom.existing_products.top_categories.length > 0 && (
              <Row k="主カテゴリ" v={atom.existing_products.top_categories.slice(0, 3).join(", ")} />
            )}
          </Section>
        )}

      </div>
    </div>
  );
}

function Section({ label, icon, children }: { label: string; icon: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-xs">{icon}</span>
        <span className="text-[9px] font-bold tracking-widest uppercase" style={{ color: "var(--text-muted)" }}>
          {label}
        </span>
      </div>
      <div className="space-y-1 pl-0.5">{children}</div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string | number | undefined | null }) {
  if (v == null || v === "") return null;
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="text-[9px] shrink-0" style={{ color: "var(--text-muted)" }}>{k}</span>
      <span className="text-[10px] text-right" style={{ color: "rgba(255,255,255,0.7)" }}>{v}</span>
    </div>
  );
}
