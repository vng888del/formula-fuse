"use client";
import { useState, useEffect } from "react";
import type { Atom, FusedFormula, AIAnalysisResult, SafetyGateResult, SavedFormula } from "@/types";
import type { HealthStatus } from "@/lib/api";
import { api } from "@/lib/api";
import { useApiKey } from "@/hooks/useApiKey";
import { AtomLibrary } from "@/components/AtomLibrary";
import { FusionCanvas } from "@/components/FusionCanvas";
import { AIReactionPanel } from "@/components/AIReactionPanel";
import { ApiKeyModal } from "@/components/ApiKeyModal";
import { FormulaHistory } from "@/components/FormulaHistory";
import { AnalyticsPanel } from "@/components/AnalyticsPanel";
import { BondGraphPanel } from "@/components/BondGraphPanel";

const NAV_ICONS = [
  { icon: "⚛", label: "Studio", active: true },
  { icon: "🔬", label: "Lab" },
  { icon: "🕸", label: "Graph" },
  { icon: "📊", label: "Analytics" },
  { icon: "📋", label: "History" },
  { icon: "⚙", label: "Settings" },
];

export default function StudioPage() {
  const { config: apiKey, save: saveApiKey, hasKey } = useApiKey();
  const [showApiModal, setShowApiModal] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [activeNav, setActiveNav] = useState(0);

  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [atoms, setAtoms] = useState<Atom[]>([]);
  const [atomsError, setAtomsError] = useState("");
  const [selectedAtoms, setSelectedAtoms] = useState<Atom[]>([]);
  const [formulaName, setFormulaName] = useState("");

  const [fused, setFused] = useState<FusedFormula | null>(null);
  const [safety, setSafety] = useState<SafetyGateResult | null>(null);
  const [analysis, setAnalysis] = useState<AIAnalysisResult | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
    api.atoms.list()
      .then(setAtoms)
      .catch(() => setAtomsError("バックエンド未接続"));
  }, []);

  const toggleAtom = (atom: Atom) => {
    setSelectedAtoms((prev) =>
      prev.find((a) => a.atom_id === atom.atom_id)
        ? prev.filter((a) => a.atom_id !== atom.atom_id)
        : [...prev, atom]
    );
    setFused(null); setSafety(null); setAnalysis(null); setSavedId(null);
  };

  const handleFuse = async () => {
    if (selectedAtoms.length < 2) return;
    if (!hasKey) { setShowApiModal(true); return; }
    setLoading(true); setError("");
    try {
      const ids = selectedAtoms.map((a) => a.atom_id);
      const [f, s] = await Promise.all([api.formula.fuse(ids), api.formula.safetyGate(ids)]);
      setFused(f); setSafety(s);
      const a = await api.formula.analyze(f, apiKey);
      setAnalysis(a);
      if (!formulaName && a.formula_name) setFormulaName(a.formula_name);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "解析エラー");
    } finally { setLoading(false); }
  };

  const handleSave = async () => {
    if (!analysis || !fused) return;
    setSaving(true);
    try {
      const name = formulaName || analysis.formula_name || selectedAtoms.map(a => a.name_ja).join(" + ");
      const saved = await api.formula.save({ name, atom_ids: selectedAtoms.map(a => a.atom_id), fused_formula: fused, ai_analysis: analysis, safety_result: safety || undefined });
      setSavedId(saved.id);
    } catch { setError("保存エラー"); } finally { setSaving(false); }
  };

  const handleSelectHistory = (f: SavedFormula) => {
    if (f.ai_analysis) setAnalysis(f.ai_analysis);
    if (f.safety_result) setSafety(f.safety_result);
    if (f.fused_formula) setFused(f.fused_formula);
    setSavedId(f.id);
    setShowHistory(false);
  };

  return (
    <div className="flex flex-col h-screen" style={{ background: "var(--bg-primary)" }}>
      {/* Top Nav */}
      <header className="shrink-0 flex items-center justify-between px-4 py-2.5"
        style={{ background: "rgba(13,13,36,0.95)", borderBottom: "1px solid var(--border)", backdropFilter: "blur(20px)" }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, var(--blue), var(--purple))", fontSize: "16px" }}>
            ⚛
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>Formula Fuse</h1>
            <p className="text-[9px] tracking-widest" style={{ color: "var(--text-muted)" }}>Fuse. Discover. Transform.</p>
          </div>
          <div className="w-px h-6 mx-2" style={{ background: "var(--border)" }} />
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
            style={{ background: "rgba(255,255,255,0.05)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
            <span>+</span>
            <span>New Project</span>
            <svg className="w-2.5 h-2.5 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* DB status indicator */}
          {health && (
            <DbStatusBadge health={health} />
          )}
          {atomsError && (
            <span className="text-[9px] px-2 py-0.5 rounded-full"
              style={{ background: "rgba(244,67,54,0.1)", color: "#f44336", border: "1px solid rgba(244,67,54,0.2)" }}>
              ⚠ {atomsError}
            </span>
          )}
          {error && (
            <span className="text-[9px] px-2 py-0.5 rounded-full cursor-pointer"
              style={{ background: "rgba(244,67,54,0.1)", color: "#f44336", border: "1px solid rgba(244,67,54,0.2)" }}
              onClick={() => setError("")}>
              ✕ {error.slice(0, 40)}
            </span>
          )}
          <button onClick={() => setShowHistory(!showHistory)}
            className="w-7 h-7 flex items-center justify-center rounded-lg text-sm transition-colors"
            style={{ color: showHistory ? "var(--blue)" : "var(--text-muted)", background: showHistory ? "rgba(79,195,247,0.1)" : "rgba(255,255,255,0.04)", border: "1px solid var(--border)" }}>
            📋
          </button>
          <button onClick={() => setShowApiModal(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors"
            style={{
              background: hasKey ? "rgba(105,240,174,0.08)" : "rgba(255,255,255,0.04)",
              border: `1px solid ${hasKey ? "rgba(105,240,174,0.2)" : "var(--border)"}`,
              color: hasKey ? "var(--green)" : "var(--text-secondary)",
            }}>
            {hasKey ? `✅ ${apiKey.provider}` : "🔑 API Key"}
          </button>
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold"
            style={{ background: "linear-gradient(135deg, var(--purple), var(--blue))", color: "white" }}>
            DR
          </div>
        </div>
      </header>

      {/* History dropdown */}
      {showHistory && (
        <div className="shrink-0 px-4 py-3" style={{ borderBottom: "1px solid var(--border)", background: "rgba(13,13,36,0.95)" }}>
          <h3 className="text-xs font-semibold mb-2" style={{ color: "var(--text-secondary)" }}>Formula 履歴</h3>
          <FormulaHistory onSelect={handleSelectHistory} />
        </div>
      )}

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Icon nav */}
        <div className="w-14 shrink-0 flex flex-col items-center py-3 gap-1"
          style={{ background: "rgba(13,13,36,0.8)", borderRight: "1px solid var(--border)" }}>
          {NAV_ICONS.map((item, i) => (
            <button
              key={i}
              onClick={() => {
                if (i === 2) { setActiveNav(n => n === 2 ? 0 : 2); return; }
                if (i === 3) { setActiveNav(n => n === 3 ? 0 : 3); return; }
                if (i === 4) { setShowHistory(h => !h); return; }
                if (i === 5) { setShowApiModal(true); return; }
                setActiveNav(i);
              }}
              title={item.label}
              className="w-9 h-9 flex items-center justify-center rounded-lg text-sm transition-all"
              style={{
                background: (i === 4 && showHistory) || activeNav === i ? "rgba(79,195,247,0.12)" : "transparent",
                color: (i === 4 && showHistory) || activeNav === i ? "var(--blue)" : "var(--text-muted)",
                border: (i === 4 && showHistory) || activeNav === i ? "1px solid rgba(79,195,247,0.2)" : "1px solid transparent",
              }}
            >
              {item.icon}
            </button>
          ))}
        </div>

        {/* Full-screen alternate views */}
        {activeNav === 2 ? (
          <div className="flex-1 overflow-hidden">
            <BondGraphPanel atoms={atoms} onClose={() => setActiveNav(0)} />
          </div>
        ) : activeNav === 3 ? (
          <div className="flex-1 overflow-hidden">
            <AnalyticsPanel atoms={atoms} onClose={() => setActiveNav(0)} />
          </div>
        ) : (
          <>
            {/* Atom Library */}
            <div className="w-64 shrink-0" style={{ borderRight: "1px solid var(--border)" }}>
              <AtomLibrary
                atoms={atoms}
                selectedIds={selectedAtoms.map((a) => a.atom_id)}
                onToggle={toggleAtom}
              />
            </div>

            {/* Fusion Canvas */}
            <div className="flex-1" style={{ borderRight: "1px solid var(--border)" }}>
              <FusionCanvas
                selectedAtoms={selectedAtoms}
                onRemove={(id) => { const a = selectedAtoms.find(x => x.atom_id === id); if (a) toggleAtom(a); }}
                formulaName={formulaName}
                onFormulaNameChange={setFormulaName}
                onFuse={handleFuse}
                loading={loading}
                fused={fused}
                analysisComplete={!!analysis}
              />
            </div>

            {/* AI Panel */}
            <div className="w-80 shrink-0">
              <AIReactionPanel
                analysis={analysis}
                safety={safety}
                fused={fused}
                formulaId={savedId}
                onSave={handleSave}
                saving={saving}
              />
            </div>
          </>
        )}
      </div>

      {showApiModal && (
        <ApiKeyModal current={apiKey} onSave={saveApiKey} onClose={() => setShowApiModal(false)} />
      )}
    </div>
  );
}

function DbStatusBadge({ health }: { health: HealthStatus }) {
  const { db } = health;

  if (db.persistent) {
    const label = db.mode === "supabase" ? "Supabase" : "PostgreSQL";
    return (
      <span className="text-[9px] px-2 py-0.5 rounded-full flex items-center gap-1"
        style={{ background: "rgba(105,240,174,0.08)", color: "var(--green)", border: "1px solid rgba(105,240,174,0.2)" }}>
        <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: "var(--green)" }} />
        {label}
      </span>
    );
  }

  if (db.status === "in_memory") {
    return (
      <span
        className="text-[9px] px-2 py-0.5 rounded-full flex items-center gap-1 cursor-help"
        title="再起動するとデータが消えます。python3 scripts/setup_db.py でSupabase を設定してください。"
        style={{ background: "rgba(255,152,0,0.08)", color: "rgba(255,152,0,0.8)", border: "1px solid rgba(255,152,0,0.2)" }}>
        <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: "rgba(255,152,0,0.8)" }} />
        メモリ
      </span>
    );
  }

  if (db.status === "error") {
    return (
      <span className="text-[9px] px-2 py-0.5 rounded-full flex items-center gap-1"
        style={{ background: "rgba(244,67,54,0.08)", color: "#f44336", border: "1px solid rgba(244,67,54,0.2)" }}>
        <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: "#f44336" }} />
        DB エラー
      </span>
    );
  }

  return null;
}
