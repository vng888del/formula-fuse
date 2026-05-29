"use client";
import type { Atom } from "@/types";
import { ATOM_TYPE_CONFIG, getAtomAbbrev } from "@/lib/atomColors";

interface Props {
  atom: Atom;
  selected: boolean;
  onClick: (atom: Atom) => void;
  onDetailClick?: (atom: Atom) => void;
  size?: "sm" | "md";
}

const GRAS_DOT: Record<string, { color: string; label: string }> = {
  GRAS:         { color: "#69f0ae", label: "GRAS" },
  NDI:          { color: "#4fc3f7", label: "NDI" },
  food_additive:{ color: "#ffd54f", label: "食品添加物" },
  unknown:      { color: "rgba(255,255,255,0.25)", label: "未確認" },
};

export function AtomCard({ atom, selected, onClick, onDetailClick, size = "md" }: Props) {
  const cfg = ATOM_TYPE_CONFIG[atom.atom_type];
  const abbrev = getAtomAbbrev(atom);
  const outerSize = size === "sm" ? 64 : 80;
  const innerSize = size === "sm" ? 52 : 64;
  const grasCfg = atom.gras ? GRAS_DOT[atom.gras.status] ?? GRAS_DOT.unknown : null;
  const evidenceCount = atom.pubmed_evidence?.length ?? 0;

  return (
    <button
      onClick={() => onClick(atom)}
      className="flex flex-col items-center gap-1.5 group transition-transform hover:scale-105 active:scale-95 cursor-pointer"
    >
      <div
        className="relative flex items-center justify-center rounded-full transition-all duration-300"
        style={{
          width: outerSize,
          height: outerSize,
          background: selected
            ? `radial-gradient(circle, ${cfg.color}22 0%, transparent 70%)`
            : "transparent",
          boxShadow: selected
            ? `0 0 20px ${cfg.glow}, 0 0 40px ${cfg.glow.replace("0.5", "0.2")}`
            : "none",
        }}
      >
        <div
          className="absolute rounded-full border animate-spin-slow"
          style={{
            width: outerSize - 4,
            height: outerSize - 4,
            borderColor: selected ? cfg.color : "rgba(255,255,255,0.1)",
            borderStyle: "dashed",
            borderWidth: 1,
            opacity: selected ? 0.6 : 0.2,
          }}
        />
        {selected && (
          <>
            <div className="orbit-dot orbit-dot-1" style={{ background: cfg.color }} />
            <div className="orbit-dot orbit-dot-2" style={{ background: cfg.color }} />
            <div className="orbit-dot orbit-dot-3" style={{ background: `${cfg.color}88` }} />
          </>
        )}
        <div
          className="relative z-10 flex items-center justify-center rounded-full font-bold tracking-wide transition-all duration-300"
          style={{
            width: innerSize,
            height: innerSize,
            background: selected
              ? `radial-gradient(circle at 35% 35%, ${cfg.color}55, ${cfg.color}18 60%, rgba(0,0,0,0.6))`
              : `radial-gradient(circle at 35% 35%, rgba(255,255,255,0.08), rgba(0,0,0,0.5))`,
            border: `1.5px solid ${selected ? cfg.color : "rgba(255,255,255,0.12)"}`,
            boxShadow: selected ? `inset 0 0 20px ${cfg.glow}` : "none",
            color: selected ? cfg.color : "rgba(255,255,255,0.6)",
          }}
        >
          <span className={abbrev.length <= 2 ? "text-sm font-bold" : "text-[10px] font-bold leading-none text-center"}>
            {abbrev}
          </span>
        </div>

        {/* GRAS status dot — top-right corner */}
        {grasCfg && (
          <div
            className="absolute top-0 right-0 z-20 rounded-full"
            title={grasCfg.label}
            style={{
              width: 10,
              height: 10,
              background: grasCfg.color,
              boxShadow: `0 0 4px ${grasCfg.color}`,
              border: "1.5px solid rgba(0,0,0,0.6)",
            }}
          />
        )}

        {/* PubMed count — bottom-left corner */}
        {evidenceCount > 0 && (
          <div
            className="absolute bottom-0 left-0 z-20 rounded-full flex items-center justify-center"
            title={`PubMed ${evidenceCount}件`}
            style={{
              width: 14,
              height: 14,
              background: "rgba(79,195,247,0.15)",
              border: "1px solid rgba(79,195,247,0.4)",
            }}
          >
            <span style={{ fontSize: 7, color: "rgba(79,195,247,0.9)", fontWeight: 700, lineHeight: 1 }}>
              {evidenceCount}
            </span>
          </div>
        )}
      </div>

      {/* Name + detail link */}
      <div className="flex flex-col items-center gap-0.5">
        <span
          className="text-[10px] font-medium text-center leading-tight max-w-18 line-clamp-2 transition-colors"
          style={{ color: selected ? cfg.color : "rgba(255,255,255,0.5)" }}
        >
          {atom.name_ja}
        </span>
        {onDetailClick && (atom.compound || atom.uniprot || atom.supplier_info || atom.usda) && (
          <button
            onClick={(e) => { e.stopPropagation(); onDetailClick(atom); }}
            className="text-[8px] leading-none opacity-0 group-hover:opacity-60 hover:opacity-100! transition-opacity"
            style={{ color: "var(--blue)" }}
          >
            詳細 →
          </button>
        )}
      </div>
    </button>
  );
}
