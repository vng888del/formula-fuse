"use client";
import type { Atom } from "@/types";
import { atomTypeColor, atomTypeLabel } from "@/lib/utils";

interface Props {
  selectedAtoms: Atom[];
  onRemove: (atomId: string) => void;
  formulaName: string;
  onFormulaNameChange: (name: string) => void;
  onFuse: () => void;
  loading: boolean;
}

export function FormulaCanvas({
  selectedAtoms,
  onRemove,
  formulaName,
  onFormulaNameChange,
  onFuse,
  loading,
}: Props) {
  return (
    <div className="flex flex-col h-full p-4 space-y-4">
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Formula名（任意）</label>
        <input
          type="text"
          value={formulaName}
          onChange={(e) => onFormulaNameChange(e.target.value)}
          placeholder="例: Fermented Wheat Protein Support Formula"
          className="w-full border rounded-lg px-3 py-2 text-sm"
        />
      </div>

      <div className="flex-1">
        <div className="text-xs font-medium text-gray-500 mb-2">
          選択Atom ({selectedAtoms.length})
        </div>

        {selectedAtoms.length === 0 ? (
          <div className="h-32 border-2 border-dashed rounded-xl flex items-center justify-center text-gray-400 text-sm">
            左のAtom Libraryから選択してください
          </div>
        ) : (
          <div className="space-y-2">
            {selectedAtoms.map((atom) => (
              <div
                key={atom.atom_id}
                className="flex items-center gap-2 bg-white border rounded-lg p-2.5"
              >
                <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${atomTypeColor(atom.atom_type)}`}>
                  {atomTypeLabel(atom.atom_type)}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{atom.name_ja}</div>
                  <div className="text-xs text-gray-400 truncate">{atom.name_en}</div>
                </div>
                <button
                  onClick={() => onRemove(atom.atom_id)}
                  className="text-gray-300 hover:text-red-400 text-lg leading-none shrink-0"
                  aria-label="Remove"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-2">
        {selectedAtoms.length >= 2 && (
          <div className="text-xs text-gray-400 text-center">
            {selectedAtoms.length}個のAtomが選択されています
          </div>
        )}
        <button
          onClick={onFuse}
          disabled={selectedAtoms.length < 2 || loading}
          className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-bold text-sm disabled:opacity-40 disabled:cursor-not-allowed hover:from-blue-700 hover:to-purple-700 transition-all"
        >
          {loading ? "解析中..." : "⚗️ Fuse & Analyze"}
        </button>
        {selectedAtoms.length < 2 && (
          <p className="text-xs text-center text-gray-400">2つ以上のAtomを選択してください</p>
        )}
      </div>
    </div>
  );
}
