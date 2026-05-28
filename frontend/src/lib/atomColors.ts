import type { AtomType } from "@/types";

export const ATOM_TYPE_CONFIG: Record<AtomType, {
  color: string;
  glow: string;
  bg: string;
  ring: string;
  label: string;
  abbrevColor: string;
}> = {
  ingredient: {
    color: "#4fc3f7",
    glow: "rgba(79,195,247,0.5)",
    bg: "radial-gradient(135deg, #1a3a5c 0%, #0d1f36 100%)",
    ring: "rgba(79,195,247,0.3)",
    label: "原材料",
    abbrevColor: "#4fc3f7",
  },
  microbe: {
    color: "#ce93d8",
    glow: "rgba(206,147,216,0.5)",
    bg: "radial-gradient(135deg, #3a1a5c 0%, #1f0d36 100%)",
    ring: "rgba(206,147,216,0.3)",
    label: "菌",
    abbrevColor: "#ce93d8",
  },
  enzyme: {
    color: "#69f0ae",
    glow: "rgba(105,240,174,0.5)",
    bg: "radial-gradient(135deg, #1a3a2a 0%, #0d1f14 100%)",
    ring: "rgba(105,240,174,0.3)",
    label: "酵素",
    abbrevColor: "#69f0ae",
  },
  condition: {
    color: "#ffd54f",
    glow: "rgba(255,213,79,0.5)",
    bg: "radial-gradient(135deg, #3a3000 0%, #1f1900 100%)",
    ring: "rgba(255,213,79,0.3)",
    label: "条件",
    abbrevColor: "#ffd54f",
  },
  goal: {
    color: "#f48fb1",
    glow: "rgba(244,143,177,0.5)",
    bg: "radial-gradient(135deg, #3a1a2a 0%, #1f0d14 100%)",
    ring: "rgba(244,143,177,0.3)",
    label: "目的",
    abbrevColor: "#f48fb1",
  },
  process: {
    color: "#80deea",
    glow: "rgba(128,222,234,0.5)",
    bg: "radial-gradient(135deg, #0a2a2e 0%, #05191c 100%)",
    ring: "rgba(128,222,234,0.3)",
    label: "工程",
    abbrevColor: "#80deea",
  },
};

export function getAtomAbbrev(atom: { name_ja: string; name_en: string; atom_type: AtomType }): string {
  const n = atom.name_ja;
  if (n.match(/pH/i)) return "pH";
  if (n.match(/℃|°C/)) return "°C";
  if (n.match(/h発酵|h$/)) {
    const m = n.match(/(\d+)h/);
    return m ? `${m[1]}h` : "h";
  }
  const en = atom.name_en;
  const words = en.split(/[\s_-]+/).filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return n.slice(0, 2);
}
