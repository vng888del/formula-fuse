"use client";
import { useState, useEffect } from "react";
import type { Atom, RegulatoryCheckResult, RegulatoryCheckItem } from "@/types";
import { api } from "@/lib/api";

const STATUS_CONFIG: Record<string, { color: string; icon: string; label: string }> = {
  pass: { color: "#69f0ae", icon: "✓", label: "OK" },
  warn: { color: "#ffd54f", icon: "⚠", label: "注意" },
  fail: { color: "#ef5350", icon: "✕", label: "NG" },
  info: { color: "#4fc3f7", icon: "ℹ", label: "確認" },
};

const OVERALL_CONFIG: Record<string, { color: string; bg: string }> = {
  "概ね問題なし":     { color: "#69f0ae", bg: "rgba(105,240,174,0.08)" },
  "注意事項あり":     { color: "#ffd54f", bg: "rgba(255,213,79,0.08)" },
  "要専門家確認":     { color: "#ef5350", bg: "rgba(239,83,80,0.08)" },
};

const MARKET_OPTIONS = ["JP", "US", "ALL"];

interface Props {
  selectedAtoms: Atom[];
  onClose: () => void;
}

function CheckItem({ item }: { item: RegulatoryCheckItem }) {
  const [open, setOpen] = useState(false);
  const cfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.info;
  return (
    <button
      onClick={() => setOpen(o => !o)}
      className="w-full rounded-lg px-3 py-2 text-left transition-all"
      style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-center gap-2">
        <span className="w-4 h-4 rounded-full flex items-center justify-center shrink-0 text-[8px] font-bold"
          style={{ background: `${cfg.color}15`, color: cfg.color, border: `1px solid ${cfg.color}30` }}>
          {cfg.icon}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-[9px] font-medium leading-tight truncate" style={{ color: "var(--text-primary)" }}>{item.item}</p>
          <p className="text-[8px]" style={{ color: "var(--text-muted)" }}>{item.category}</p>
        </div>
      </div>
      {open && (
        <p className="mt-1.5 text-[8px] leading-relaxed pl-6" style={{ color: "rgba(255,255,255,0.5)" }}>{item.detail}</p>
      )}
    </button>
  );
}

export function RegulatoryPanel({ selectedAtoms, onClose }: Props) {
  const [result, setResult] = useState<RegulatoryCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [market, setMarket] = useState("JP");

  const check = async (m = market) => {
    if (selectedAtoms.length === 0) return;
    setLoading(true);
    try {
      const r = await api.formula.regulatoryCheck(selectedAtoms.map(a => a.atom_id), m);
      setResult(r);
    } catch { /* silently fail */ } finally { setLoading(false); }
  };

  useEffect(() => { check(); }, [selectedAtoms.length, market]);

  if (selectedAtoms.length === 0) {
    return (
      <div className="flex flex-col h-full items-center justify-center px-6"
        style={{ background: "var(--bg-secondary)" }}>
        <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
          Atomを選択すると規制チェックリストを表示します
        </p>
      </div>
    );
  }

  const overallCfg = result ? (OVERALL_CONFIG[result.overall_status] || OVERALL_CONFIG["注意事項あり"]) : null;

  const grouped = result
    ? result.checklist.reduce((acc, item) => {
        (acc[item.category] ??= []).push(item);
        return acc;
      }, {} as Record<string, RegulatoryCheckItem[]>)
    : {};

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-secondary)", fontSize: 11 }}>
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between shrink-0"
        style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          <span>📜</span>
          <div>
            <p className="font-bold text-xs" style={{ color: "var(--text-primary)" }}>規制チェックリスト</p>
            <p className="text-[9px]" style={{ color: "var(--text-muted)" }}>Regulatory Compliance</p>
          </div>
        </div>
        <button onClick={onClose} className="w-6 h-6 flex items-center justify-center rounded-full"
          style={{ color: "var(--text-muted)", background: "rgba(255,255,255,0.05)" }}>×</button>
      </div>

      {/* Market selector */}
      <div className="px-4 py-2 flex gap-1.5 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        {MARKET_OPTIONS.map(m => (
          <button key={m}
            onClick={() => setMarket(m)}
            className="px-3 py-1 rounded-lg text-[9px] font-bold transition-all"
            style={{
              background: market === m ? "rgba(79,195,247,0.15)" : "rgba(255,255,255,0.04)",
              border: `1px solid ${market === m ? "rgba(79,195,247,0.3)" : "var(--border)"}`,
              color: market === m ? "var(--blue)" : "var(--text-muted)",
            }}>
            {m}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {loading && (
          <div className="flex justify-center py-4">
            <div className="w-5 h-5 rounded-full border-2 animate-spin"
              style={{ borderColor: "var(--blue)", borderTopColor: "transparent" }} />
          </div>
        )}

        {result && !loading && overallCfg && (
          <>
            {/* Overall status */}
            <div className="rounded-xl p-3 text-center"
              style={{ background: overallCfg.bg, border: `1px solid ${overallCfg.color}25` }}>
              <p className="text-[9px] font-bold tracking-widest uppercase mb-1" style={{ color: overallCfg.color }}>
                OVERALL STATUS
              </p>
              <p className="text-sm font-bold" style={{ color: overallCfg.color }}>{result.overall_status}</p>
              <p className="text-[9px] mt-1" style={{ color: "rgba(255,255,255,0.4)" }}>
                {result.checklist.length}項目 / 市場: {result.target_market}
              </p>
            </div>

            {/* Grouped checklist */}
            {Object.entries(grouped).map(([cat, items]) => (
              <div key={cat}>
                <p className="text-[9px] font-bold tracking-widest uppercase mb-1.5" style={{ color: "var(--text-muted)" }}>
                  {cat}
                </p>
                <div className="space-y-1">
                  {items.map((item, i) => <CheckItem key={i} item={item} />)}
                </div>
              </div>
            ))}

            {/* Required actions */}
            {result.required_actions.length > 0 && (
              <div>
                <p className="text-[9px] font-bold tracking-widest uppercase mb-1.5" style={{ color: "#ffd54f" }}>
                  必要アクション
                </p>
                <div className="space-y-1">
                  {result.required_actions.map((a, i) => (
                    <div key={i} className="rounded-lg px-3 py-1.5"
                      style={{ background: "rgba(255,213,79,0.05)", border: "1px solid rgba(255,213,79,0.15)" }}>
                      <p className="text-[9px] leading-relaxed" style={{ color: "rgba(255,213,79,0.8)" }}>→ {a}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Expert reviews */}
            {result.expert_reviews.length > 0 && (
              <div>
                <p className="text-[9px] font-bold tracking-widest uppercase mb-1.5" style={{ color: "#ef5350" }}>
                  専門家レビュー必須
                </p>
                <div className="space-y-1">
                  {result.expert_reviews.map((r, i) => (
                    <div key={i} className="rounded-lg px-3 py-1.5"
                      style={{ background: "rgba(239,83,80,0.05)", border: "1px solid rgba(239,83,80,0.2)" }}>
                      <p className="text-[9px] leading-relaxed" style={{ color: "rgba(239,83,80,0.8)" }}>⚠ {r}</p>
                    </div>
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
