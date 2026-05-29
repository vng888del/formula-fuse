"use client";
import { useState, useEffect } from "react";
import type { Atom, CostEstimateResult } from "@/types";
import { api } from "@/lib/api";

const TIER_COLOR: Record<string, string> = {
  low:       "#69f0ae",
  medium:    "#4fc3f7",
  high:      "#ffd54f",
  very_high: "#ef5350",
};

const TIER_LABEL: Record<string, string> = {
  low:       "低コスト",
  medium:    "中コスト",
  high:      "高コスト",
  very_high: "超高コスト",
};

interface Props {
  selectedAtoms: Atom[];
  onClose: () => void;
}

export function CostPanel({ selectedAtoms, onClose }: Props) {
  const [result, setResult] = useState<CostEstimateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [dailyDose, setDailyDose] = useState(1.0);
  const [batchSize, setBatchSize] = useState(10.0);

  const estimate = async () => {
    if (selectedAtoms.length === 0) return;
    setLoading(true);
    try {
      const r = await api.formula.costEstimate(
        selectedAtoms.map(a => a.atom_id),
        dailyDose,
        batchSize
      );
      setResult(r);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { estimate(); }, [selectedAtoms.length]);

  if (selectedAtoms.length === 0) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-3 px-6"
        style={{ background: "var(--bg-secondary)" }}>
        <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
          Atomを選択すると原価試算を表示します
        </p>
      </div>
    );
  }

  const tierColor = result ? (TIER_COLOR[result.cost_tier] || "var(--text-secondary)") : "var(--text-muted)";

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--bg-secondary)", fontSize: 11 }}>
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          <span>💰</span>
          <div>
            <p className="font-bold text-xs" style={{ color: "var(--text-primary)" }}>原価シミュレーター</p>
            <p className="text-[9px]" style={{ color: "var(--text-muted)" }}>概算製造コスト</p>
          </div>
        </div>
        <button onClick={onClose} className="w-6 h-6 flex items-center justify-center rounded-full"
          style={{ color: "var(--text-muted)", background: "rgba(255,255,255,0.05)" }}>×</button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* Parameters */}
        <div className="rounded-xl p-3 space-y-2" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid var(--border)" }}>
          <p className="text-[9px] font-bold tracking-widest uppercase" style={{ color: "var(--text-muted)" }}>試算パラメータ</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[9px] block mb-0.5" style={{ color: "var(--text-muted)" }}>1日合計摂取量 (g)</label>
              <input type="number" min={0.1} max={50} step={0.1} value={dailyDose}
                onChange={e => setDailyDose(parseFloat(e.target.value) || 1)}
                onBlur={estimate}
                className="w-full rounded px-2 py-1 text-xs outline-none"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
            </div>
            <div>
              <label className="text-[9px] block mb-0.5" style={{ color: "var(--text-muted)" }}>バッチサイズ (kg)</label>
              <input type="number" min={1} max={1000} step={1} value={batchSize}
                onChange={e => setBatchSize(parseFloat(e.target.value) || 10)}
                onBlur={estimate}
                className="w-full rounded px-2 py-1 text-xs outline-none"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
            </div>
          </div>
        </div>

        {loading && (
          <div className="flex justify-center py-4">
            <div className="w-5 h-5 rounded-full border-2 border-t-transparent animate-spin"
              style={{ borderColor: "var(--blue)", borderTopColor: "transparent" }} />
          </div>
        )}

        {result && !loading && (
          <>
            {/* Summary */}
            <div className="rounded-xl p-3 text-center" style={{ background: `${tierColor}0a`, border: `1px solid ${tierColor}25` }}>
              <p className="text-[9px] font-bold tracking-widest uppercase mb-1" style={{ color: tierColor }}>
                {TIER_LABEL[result.cost_tier] || result.cost_tier}
              </p>
              <p className="text-lg font-bold" style={{ color: tierColor }}>{result.estimated_cost_per_kg}</p>
              <p className="text-[10px] mt-1" style={{ color: "rgba(255,255,255,0.5)" }}>
                1serving あたり {result.estimated_cost_per_serving}
              </p>
            </div>

            {/* Breakdown */}
            <div>
              <p className="text-[9px] font-bold tracking-widest uppercase mb-2" style={{ color: "var(--text-muted)" }}>原料別内訳</p>
              <div className="space-y-1.5">
                {result.cost_breakdown.map(item => {
                  const c = TIER_COLOR[item.price_tier] || "rgba(255,255,255,0.3)";
                  return (
                    <div key={item.atom_id} className="rounded-lg px-3 py-2"
                      style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border)" }}>
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-[10px] font-medium" style={{ color: "var(--text-primary)" }}>{item.name_ja}</span>
                        <span className="text-[8px] px-1.5 py-0.5 rounded-full font-bold"
                          style={{ background: `${c}15`, color: c, border: `1px solid ${c}30` }}>
                          {item.price_tier}
                        </span>
                      </div>
                      <p className="text-[9px]" style={{ color: "var(--text-muted)" }}>{item.cost_per_kg_range} / バッチ {item.batch_cost_range}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Notes */}
            <div>
              <p className="text-[9px] font-bold tracking-widest uppercase mb-2" style={{ color: "var(--text-muted)" }}>注意事項</p>
              <div className="space-y-1">
                {result.notes.map((n, i) => (
                  <p key={i} className="text-[9px] leading-relaxed" style={{ color: "rgba(255,255,255,0.4)" }}>• {n}</p>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
