#!/usr/bin/env python3
"""
generate_docs.py — Formula Fuse Studio 進捗ドキュメント自動生成スクリプト

実行: python3 scripts/generate_docs.py
生成: docs/progress.md  +  project.md 動的セクション更新
"""

import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "seed-atoms"
BACKEND_DIR = ROOT / "backend" / "app"
FRONTEND_DIR = ROOT / "frontend" / "src"
DOCS_DIR = ROOT / "docs"

SOURCE_PATTERNS = [
    DATA_DIR / "food-bio-atoms.json",
    DATA_DIR / "risk-tags.json",
    DATA_DIR / "bond-rules.json",
    BACKEND_DIR / "routers" / "atoms.py",
    BACKEND_DIR / "routers" / "formulas.py",
    BACKEND_DIR / "services" / "ai_router.py",
    BACKEND_DIR / "services" / "fuse_engine.py",
    BACKEND_DIR / "services" / "risk_gate.py",
    BACKEND_DIR / "services" / "report_generator.py",
    BACKEND_DIR / "db" / "database.py",
    DOCS_DIR / "data-sources.md",
]

HASH_MARKER = "<!-- src-hash:"


def compute_source_hash() -> str:
    h = hashlib.md5()
    for p in sorted(SOURCE_PATTERNS):
        if p.exists():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:12]


def read_embedded_hash(progress_file: Path) -> Optional[str]:
    if not progress_file.exists():
        return None
    for line in progress_file.read_text(encoding="utf-8").splitlines():
        if line.startswith(HASH_MARKER):
            return line.removeprefix(HASH_MARKER).rstrip(" -->").strip()
    return None


# ── 対象セグメント別の分母 ─────────────────────────────────────────────────────
# フィールドによって「意味のある対象 atom_type」が異なる。
# compound/gras/usda/supplier: ingredient のみ（純粋な食材・素材）
# uniprot:                      ingredient + microbe + enzyme（生体分子）
# pubmed:                       ingredient（臨床エビデンスを持つ素材）
# market_trends/existing_prod:  ingredient（市場データの対象）
# patent_landscape:             ingredient + microbe + enzyme（IP対象）

def _seg(atoms: list, types) -> list:
    if isinstance(types, str):
        types = {types}
    return [a for a in atoms if a.get("atom_type") in types]


def coverage(atoms: list, field: str, types) -> tuple[int, int]:
    """(持つ件数, 対象件数) を返す"""
    target = _seg(atoms, types)
    n = sum(1 for a in target if a.get(field))
    return n, len(target)


ENRICH_SPEC = [
    # (field, label, target_types, 完了閾値%)
    ("compound",          "PubChem 化合物データ",         "ingredient",                        80),
    ("uniprot",           "UniProt 酵素・微生物データ",    {"ingredient", "microbe", "enzyme"}, 70),
    ("gras",              "FDA GRAS ステータス",           "ingredient",                        90),
    ("usda",              "USDA 栄養データ",               "ingredient",                        40),
    ("pubmed_evidence",   "PubMed 文献エビデンス",          "ingredient",                        95),
    ("supplier_info",     "サプライヤー・OEM 情報",         "ingredient",                        90),
    ("patent_landscape",  "特許ランドスケープ",             {"ingredient", "microbe", "enzyme"}, 50),
    ("market_trends",     "Google Trends 市場需要",        "ingredient",                        80),
    ("existing_products", "Open Food Facts 既存製品",      "ingredient",                        70),
]


# ── 完了基準 ──────────────────────────────────────────────────────────────────
# Phase i が「完了」かを判定する。
# 「any有り」ではなく閾値カバレッジで判定する。

def _pct(atoms, field, types) -> float:
    n, total = coverage(atoms, field, types)
    return (n / total * 100) if total else 0.0

def phase_done(phase_id: int, atoms: list) -> tuple[bool, str]:
    """(done: bool, reason: str) を返す"""
    if phase_id == 0:
        return True, "シードJSON存在"
    if phase_id == 1:
        pc = _pct(atoms, "compound", "ingredient")
        ud = _pct(atoms, "usda", "ingredient")
        done = pc >= 80
        note = f"PubChem {pc:.0f}% / USDA {ud:.0f}%（基準: PubChem ≥ 80%）"
        return done, note
    if phase_id == 2:
        un = _pct(atoms, "uniprot", {"ingredient", "microbe", "enzyme"})
        pm = _pct(atoms, "pubmed_evidence", "ingredient")
        done = pm >= 95
        note = f"PubMed {pm:.0f}% / UniProt {un:.0f}%（基準: PubMed ≥ 95%）"
        return done, note
    if phase_id == 3:
        gr = _pct(atoms, "gras", "ingredient")
        done = gr >= 90
        note = f"GRAS {gr:.0f}%（基準: ingredient ≥ 90%）"
        return done, note
    if phase_id == 4:
        su = _pct(atoms, "supplier_info", "ingredient")
        pt = _pct(atoms, "patent_landscape", {"ingredient", "microbe", "enzyme"})
        done = su >= 90 and pt >= 50
        note = f"Supplier {su:.0f}% / Patent {pt:.0f}%（基準: Supplier ≥ 90% & Patent ≥ 50%）"
        return done, note
    if phase_id == 5:
        tr = _pct(atoms, "market_trends", "ingredient")
        ep = _pct(atoms, "existing_products", "ingredient")
        done = tr >= 80 and ep >= 70
        note = f"Trends {tr:.0f}% / OpenFoodFacts {ep:.0f}%（基準: Trends ≥ 80% & OFF ≥ 70%）"
        return done, note
    return False, "不明"


def phase_label(done: bool, note: str) -> str:
    if done:
        return f"✅ 完了 — {note}"
    return f"⚠️ 進行中 — {note}"


# ── MVP チェックリスト ────────────────────────────────────────────────────────

def _file_exists(*parts):
    return (ROOT / Path(*parts)).exists()

def _has_content(path, keyword):
    p = ROOT / path
    return p.exists() and keyword in p.read_text(encoding="utf-8")

MVP_ITEMS = [
    ("Atom を登録できる（シードデータ）",
     lambda: _file_exists("data/seed-atoms/food-bio-atoms.json"),
     "シードJSON存在チェック"),
    ("Atom を UI で選択できる",
     lambda: _file_exists("frontend/src/components/AtomLibrary.tsx"),
     "AtomLibrary.tsx"),
    ("複数 Atom を Fuse して Formula を生成できる",
     lambda: _file_exists("backend/app/services/fuse_engine.py"),
     "fuse_engine.py"),
    ("Formula を AI 解析できる（BYOK）",
     lambda: _file_exists("backend/app/services/ai_router.py"),
     "ai_router.py"),
    ("Risk Gate で Green/Yellow/Red/Black を判定できる",
     lambda: _file_exists("backend/app/services/risk_gate.py"),
     "risk_gate.py"),
    ("AI 出力を構造化 JSON で受け取る",
     lambda: _has_content("backend/app/models/formula.py", "AIAnalysisResult"),
     "AIAnalysisResult モデル"),
    ("Formula を保存できる（永続化）",
     lambda: _has_content("backend/app/db/database.py", "postgresql")
             or _has_content("backend/app/db/database.py", "supabase")
             or _has_content("backend/app/db/database.py", "asyncpg"),
     "PostgreSQL/Supabase 接続"),
    ("Formula を保存できる（インメモリ暫定）",
     lambda: _has_content("backend/app/db/database.py", "_formulas_store"),
     "_formulas_store（インメモリ）"),
    ("Markdown レポートを出力できる",
     lambda: _file_exists("backend/app/services/report_generator.py"),
     "report_generator.py"),
    ("BYOK 方式で API キーを使う",
     lambda: _file_exists("frontend/src/components/ApiKeyModal.tsx"),
     "ApiKeyModal.tsx"),
    ("Formula Fuse Studio の UI で動作確認できる",
     lambda: _file_exists("frontend/src/app/page.tsx"),
     "page.tsx"),
]


# ── ヘルパー ─────────────────────────────────────────────────────────────────

def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_routes(router_file: Path) -> list[dict]:
    text = router_file.read_text(encoding="utf-8")
    routes = []
    for m in re.finditer(r'@router\.(get|post|put|delete|patch)\("([^"]*)"', text):
        routes.append({"method": m.group(1).upper(), "path": m.group(2) or "/"})
    return routes


def list_components(components_dir: Path) -> list[str]:
    if not components_dir.exists():
        return []
    return sorted(
        p.name for p in components_dir.glob("*.tsx")
        if not p.name.startswith(".") and not p.name.startswith("_")
    )


def ai_providers(ai_router_file: Path) -> list[str]:
    if not ai_router_file.exists():
        return []
    text = ai_router_file.read_text(encoding="utf-8")
    return [n for n in ("openai", "claude", "gemini") if f'provider == "{n}"' in text]


def _py_files(d: Path) -> list[Path]:
    return sorted(p for p in d.glob("*.py")
                  if not p.name.startswith(".") and p.name != "__init__.py") if d.exists() else []


def _db_ok(env_file: Path) -> bool:
    if not env_file.exists():
        return False
    _placeholder = re.compile(r"your-|<[^>]+>|placeholder|example\.com", re.IGNORECASE)
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if k == "SUPABASE_URL" and v.startswith("http") and not _placeholder.search(v):
            return True
        if k == "DATABASE_URL" and v.startswith(("postgresql://", "postgres://")) and not _placeholder.search(v):
            return True
    return False


# ── 進捗.md 生成 ──────────────────────────────────────────────────────────────

def generate_progress() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    atoms: list[dict] = []
    atom_files: list[str] = []
    for p in sorted(DATA_DIR.glob("*-atoms.json")):
        if p.name.startswith(".") or p.name.startswith("._"):
            continue
        data = load_json(p)
        atoms.extend(data)
        atom_files.append(f"{p.name} ({len(data)}件)")
    tags  = load_json(DATA_DIR / "risk-tags.json")  if (DATA_DIR / "risk-tags.json").exists()  else []
    bonds = load_json(DATA_DIR / "bond-rules.json") if (DATA_DIR / "bond-rules.json").exists() else []

    atom_types = Counter(a["atom_type"] for a in atoms)
    tag_sev    = Counter(t["severity"] for t in tags)
    ingredient_atoms = _seg(atoms, "ingredient")
    n_ing = len(ingredient_atoms)

    # --- Backend ---
    all_routes: list[dict] = []
    for rf in _py_files(BACKEND_DIR / "routers"):
        for route in extract_routes(rf):
            route["file"] = rf.name
            all_routes.append(route)

    service_files = [p.name for p in _py_files(BACKEND_DIR / "services")]
    providers = ai_providers(BACKEND_DIR / "services" / "ai_router.py")
    components = list_components(FRONTEND_DIR / "components")
    hooks = sorted(p.name for p in (FRONTEND_DIR / "hooks").glob("*.ts")
                   if not p.name.startswith(".")) if (FRONTEND_DIR / "hooks").exists() else []
    lib_files = sorted(p.name for p in (FRONTEND_DIR / "lib").glob("*.ts")
                       if not p.name.startswith(".")) if (FRONTEND_DIR / "lib").exists() else []

    mvp_results = []
    for label, check_fn, detail in MVP_ITEMS:
        try:
            ok = check_fn()
        except Exception:
            ok = False
        mvp_results.append((label, ok, detail))

    done_count = sum(1 for _, ok, _ in mvp_results if ok)
    total_count = len(mvp_results)

    db_file = BACKEND_DIR / "db" / "database.py"
    env_file = ROOT / "backend" / ".env"
    db_ok_flag = False
    if db_file.exists():
        db_text = db_file.read_text(encoding="utf-8")
        if any(kw in db_text for kw in ("postgresql", "asyncpg", "supabase", "psycopg")):
            db_ok_flag = True
    db_status = "✅ PostgreSQL/Supabase 接続済み" if db_ok_flag else "⚠️ インメモリ（`_formulas_store`）— 再起動でリセット"

    lines: list[str] = []
    lines += [
        "# Formula Fuse Studio — 進捗レポート",
        "",
        f"> 自動生成: {now}",
        "> `python3 scripts/generate_docs.py` を実行すると再生成されます。",
        "",
        "---",
        "",
    ]

    bar_filled = int(done_count / total_count * 20)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    pct = int(done_count / total_count * 100)
    lines += ["## MVP 達成率", "", "```",
              f"[{bar}] {pct}%  ({done_count}/{total_count})",
              "```", ""]

    lines += ["## MVP スコープ", ""]
    for label, ok, detail in mvp_results:
        lines.append(f"- {'✅' if ok else '⬜'} **{label}**  <sub>{detail}</sub>")
    lines.append("")

    lines += ["---", "", "## データ層", "", "### Seed Atoms", "",
              "| ファイル | 件数 |", "|---|---:|"]
    for af in atom_files:
        name, cnt = af.rsplit(" (", 1)
        lines.append(f"| `{name}` | {cnt.rstrip('件)')} |")
    lines += [f"| **合計** | **{len(atoms)}** |", "",
              "| atom_type | 件数 |", "|---|---:|"]
    for t in ["ingredient", "microbe", "enzyme", "condition", "goal", "process"]:
        if atom_types.get(t):
            lines.append(f"| {t} | {atom_types[t]} |")
    lines.append("")

    # エンリッチメント — 対象別カバレッジ
    lines += [
        "### Atom エンリッチメント状況（対象タイプ別）",
        "",
        "> ⚠️ 分母は「意味のある対象 atom_type」のみ。goal/condition は化合物・栄養データの対象外。",
        "",
        "| フィールド | 付与済 / 対象 | カバレッジ | 完了基準 |",
        "|---|---:|---:|---:|",
    ]
    for field, label, types, threshold in ENRICH_SPEC:
        n, total = coverage(atoms, field, types)
        pct_e = (n / total * 100) if total else 0
        done_mark = "✅" if pct_e >= threshold else ("⚠️" if n > 0 else "⬜")
        lines.append(f"| {label} | {n} / {total} | {pct_e:.0f}% | {done_mark} ≥{threshold}% |")
    lines.append("")

    lines += ["### Risk Tags", "", "| severity | 件数 |", "|---|---:|",
              f"| **合計** | **{len(tags)}** |"]
    for sev in ["black", "red", "yellow", "green"]:
        if tag_sev.get(sev):
            lines.append(f"| {sev} | {tag_sev[sev]} |")
    lines.append("")

    lines += ["### Bond Rules", "", f"合計 **{len(bonds)}** ルール", ""]
    if bonds:
        lines += ["| bond_type | 件数 |", "|---|---:|"]
        for bt, cnt in Counter(b["bond_type"] for b in bonds).most_common():
            lines.append(f"| {bt} | {cnt} |")
    lines.append("")

    lines += ["---", "", "## バックエンド（FastAPI）", "",
              "### API エンドポイント", "",
              f"合計 **{len(all_routes)}** ルート", "",
              "| Method | Path | Router |", "|---|---|---|"]
    for r in all_routes:
        lines.append(f"| `{r['method']}` | `{r['path']}` | {r['file']} |")
    lines.append("")

    lines += ["### Services", ""]
    for sf in service_files:
        lines.append(f"- ✅ `{sf}`")
    lines.append("")

    lines += ["### AI プロバイダー対応", ""]
    for p in providers:
        lines.append(f"- ✅ {p}")
    if not providers:
        lines.append("- ⬜ 未実装")
    lines += ["", "### DB / 永続化", "", db_status, ""]

    lines += ["---", "", "## フロントエンド（Next.js）", "", "### Components", ""]
    for c in components:
        lines.append(f"- ✅ `{c}`")
    lines += ["", "### Hooks", ""]
    for h in hooks:
        lines.append(f"- ✅ `{h}`")
    lines += ["", "### Lib", ""]
    for ll in lib_files:
        lines.append(f"- ✅ `{ll}`")
    lines.append("")

    # Phase status — カバレッジ閾値判定
    phase_defs = [
        (0, "手動シード Atom"),
        (1, "PubChem / MEXT / USDA API 連携"),
        (2, "UniProt / PubMed"),
        (3, "FDA GRAS / Safety Gate 強化"),
        (4, "サプライヤー / Lens.org 特許"),
        (5, "Google Trends / Open Food Facts"),
    ]
    lines += ["---", "", "## データソース フェーズ（完了基準付き）", "",
              "| Phase | 内容 | 状態 |", "|---|---|---|"]
    for pid, desc in phase_defs:
        done, note = phase_done(pid, atoms)
        lines.append(f"| {pid} | {desc} | {phase_label(done, note)} |")
    lines.append("")

    # Next actions
    incomplete = [(label, detail) for label, ok, detail in mvp_results if not ok]
    if incomplete:
        lines += ["---", "", "## 次のアクション（未完了 MVP 項目）", ""]
        for label, detail in incomplete:
            lines.append(f"- [ ] **{label}** — `{detail}`")
        lines.append("")

    src_hash = compute_source_hash()
    file_hashes = compute_per_file_hashes()
    lines += [
        "---",
        "",
        "_このファイルは自動生成です。手動編集しても次回上書きされます。_",
        "_更新: `python3 scripts/generate_docs.py`　確認: `python3 scripts/generate_docs.py --check`_",
        "",
        f"{HASH_MARKER} {src_hash} -->",
        f"<!-- file-hashes: {json.dumps(file_hashes, separators=(',', ':'))} -->",
    ]
    return "\n".join(lines) + "\n"


# ── project.md 動的セクション更新 ────────────────────────────────────────────

def _replace_section(text: str, name: str, new_body: str) -> str:
    begin = f"<!-- BEGIN:{name} -->"
    end = f"<!-- END:{name} -->"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    replacement = f"{begin}\n{new_body.strip()}\n{end}"
    new_text, n = pattern.subn(replacement, text)
    if n == 0:
        print(f"  ⚠️  マーカー '{name}' が見つかりません — スキップ")
    return new_text


def update_project_md(atoms: list, bonds: list, tags: list, mvp_results: list) -> None:
    project_file = ROOT / "project.md"
    if not project_file.exists():
        print("⚠️  project.md が見つかりません")
        return

    text = project_file.read_text(encoding="utf-8")
    atom_types = Counter(a["atom_type"] for a in atoms)
    tag_sev    = Counter(t.get("severity", "unknown") for t in tags)
    env_file   = ROOT / "backend" / ".env"
    db_ok      = _db_ok(env_file)

    # ── current-state ─────────────────────────────────────────────────────────
    rows_cs = [
        ("Atom 選択 UI", "✅"),
        ("Fuse エンジン（Bond マッチング）", "✅"),
        ("Risk Gate（E0–E5 + GRAS注記）", "✅"),
        ("AI 解析（OpenAI / Claude / Gemini）", "✅"),
        ("Markdown レポート出力（Phase 1–5対応）", "✅"),
        ("BYOK（Bring Your Own Key）", "✅"),
        ("AtomDetailPanel（エンリッチデータ表示）",
         "✅" if (ROOT / "frontend/src/components/AtomDetailPanel.tsx").exists() else "⬜"),
        ("Bond 可視化（FusionCanvas）", "✅"),
        ("逆引き検索 SuggestPanel",
         "✅" if (ROOT / "frontend/src/components/SuggestPanel.tsx").exists() else "⬜"),
        ("原価シミュレーター CostPanel",
         "✅" if (ROOT / "frontend/src/components/CostPanel.tsx").exists() else "⬜"),
        ("配合量ガイド DosePanel",
         "✅" if (ROOT / "frontend/src/components/DosePanel.tsx").exists() else "⬜"),
        ("規制チェックリスト RegulatoryPanel",
         "✅" if (ROOT / "frontend/src/components/RegulatoryPanel.tsx").exists() else "⬜"),
    ]

    # エンリッチ行：対象別カバレッジ（ingredient専用分母）
    enrich_rows = [
        ("compound",          "Phase 1: PubChem",             "ingredient",                        80),
        ("usda",              "Phase 1: USDA 栄養データ",      "ingredient",                        40),
        ("uniprot",           "Phase 2: UniProt",              {"ingredient", "microbe", "enzyme"}, 70),
        ("pubmed_evidence",   "Phase 2: PubMed",               "ingredient",                        95),
        ("gras",              "Phase 3: FDA GRAS/Safety Gate", "ingredient",                        90),
        ("supplier_info",     "Phase 4: サプライヤー情報",      "ingredient",                        90),
        ("patent_landscape",  "Phase 4: 特許ランドスケープ",    {"ingredient", "microbe", "enzyme"}, 50),
        ("market_trends",     "Phase 5: Google Trends",        "ingredient",                        80),
        ("existing_products", "Phase 5: Open Food Facts",      "ingredient",                        70),
    ]
    for field, label, types, threshold in enrich_rows:
        n, total = coverage(atoms, field, types)
        pct = (n / total * 100) if total else 0
        if n == 0:
            rows_cs.append((label, "⬜ 0件 — 未実行"))
        elif pct >= threshold:
            rows_cs.append((label, f"✅ {n}/{total} ({pct:.0f}%) — 完了基準達成"))
        else:
            rows_cs.append((label, f"⚠️ {n}/{total} ({pct:.0f}%) — 目標{threshold}%"))

    if db_ok:
        rows_cs.append(("**Formula 保存（Supabase DB）**", "✅ 本番稼働中"))
    else:
        rows_cs.append(("Formula 保存（インメモリ暫定）", "⚠️ 動作中（再起動でリセット）"))
        rows_cs.append(("**Formula 保存（DB 永続化）**", "⬜ **未着手 ← Next**"))

    cs_lines = ["| 区分 | 状態 |", "|---|---|"]
    for label, status in rows_cs:
        cs_lines.append(f"| {label} | {status} |")
    text = _replace_section(text, "current-state", "\n".join(cs_lines))

    # ── atom-counts ───────────────────────────────────────────────────────────
    type_parts = " / ".join(
        f"{t} {atom_types.get(t, 0)}"
        for t in ["ingredient", "microbe", "enzyme", "condition", "goal"]
    )
    text = _replace_section(text, "atom-counts",
                            f"現在 **{len(atoms)} Atoms**（{type_parts}）")

    # ── bond-counts ───────────────────────────────────────────────────────────
    text = _replace_section(
        text, "bond-counts",
        f"現在 **{len(bonds)} Bond Rules**。"
        f"Risk Tags **{len(tags)}** 件"
        f"（red {tag_sev.get('red', 0)} / yellow {tag_sev.get('yellow', 0)}）。"
    )

    # ── data-phases（カバレッジ閾値ベース） ────────────────────────────────────
    phase_defs = [
        (0, "手動シード Atom"),
        (1, "PubChem / MEXT / USDA API 連携"),
        (2, "UniProt / PubMed"),
        (3, "FDA GRAS / Safety Gate 強化"),
        (4, "サプライヤー / Lens.org 特許"),
        (5, "Google Trends / Open Food Facts"),
    ]
    dp_lines = [
        "| Phase | 内容 | 状態 | 詳細 |",
        "|---|---|---|---|",
    ]
    for pid, desc in phase_defs:
        done, note = phase_done(pid, atoms)
        status = "✅ 完了" if done else "⚠️ 進行中"
        dp_lines.append(f"| {pid} | {desc} | {status} | {note} |")
    text = _replace_section(text, "data-phases", "\n".join(dp_lines))

    # ── next-steps（優先度順・動的生成） ─────────────────────────────────────
    items: list[str] = []
    i = 1

    if not db_ok:
        items.append(
            f"{i}. **[P0] DB 永続化**（MVP 未完了）\n"
            "   - `backend/.env` に SUPABASE_URL / DATABASE_URL を設定\n"
            "   - `python3 scripts/setup_db.py` を実行"
        )
        i += 1

    # Phase 1: PubChem カバレッジ不足なら優先
    pc_pct = _pct(atoms, "compound", "ingredient")
    if pc_pct < 80:
        items.append(
            f"{i}. **[P1] PubChem エンリッチ** — ingredient {pc_pct:.0f}% → 目標 80%\n"
            "   - `python3 scripts/enrich_pubchem.py --missing`"
        )
        i += 1

    # Phase 2: PubMed
    pm_pct = _pct(atoms, "pubmed_evidence", "ingredient")
    if pm_pct < 95:
        items.append(
            f"{i}. **[P1] PubMed エンリッチ** — ingredient {pm_pct:.0f}% → 目標 95%\n"
            "   - `python3 scripts/enrich_pubmed.py --missing`"
        )
        i += 1

    # Phase 3: GRAS
    gr_pct = _pct(atoms, "gras", "ingredient")
    if gr_pct < 90:
        items.append(
            f"{i}. **[P1] FDA GRAS エンリッチ** — ingredient {gr_pct:.0f}% → 目標 90%\n"
            "   - `python3 scripts/enrich_fda_gras.py --missing`"
        )
        i += 1

    # Phase 5: Open Food Facts
    ep_pct = _pct(atoms, "existing_products", "ingredient")
    if ep_pct < 70:
        items.append(
            f"{i}. **[P2] Open Food Facts 完了** → Supabase 再同期\n"
            f"   - ingredient {ep_pct:.0f}% → 目標 70%\n"
            "   - `python3 scripts/enrich_open_food_facts.py --missing`\n"
            "   - 完了後: `python3 scripts/sync_atoms_supabase.py`"
        )
        i += 1

    # Phase 5: Google Trends
    tr_pct = _pct(atoms, "market_trends", "ingredient")
    if tr_pct < 80:
        items.append(
            f"{i}. **[P2] Google Trends** — ingredient {tr_pct:.0f}% → 目標 80%\n"
            "   - 数時間待機後に `python3 scripts/enrich_google_trends.py --force`"
        )
        i += 1

    # USDA
    ud_pct = _pct(atoms, "usda", "ingredient")
    if ud_pct < 40:
        items.append(
            f"{i}. **[P2] USDA 栄養データ** — ingredient {ud_pct:.0f}% → 目標 40%\n"
            "   - `USDA_API_KEY=YOUR_KEY python3 scripts/import_usda.py`\n"
            "   - 無料取得: https://api.nal.usda.gov/"
        )
        i += 1

    # UniProt
    un_pct = _pct(atoms, "uniprot", {"ingredient", "microbe", "enzyme"})
    if un_pct < 70:
        items.append(
            f"{i}. **[P2] UniProt エンリッチ** — bio-atoms {un_pct:.0f}% → 目標 70%\n"
            "   - `python3 scripts/enrich_uniprot.py --missing`"
        )
        i += 1

    # Patent (低優先度)
    pt_pct = _pct(atoms, "patent_landscape", {"ingredient", "microbe", "enzyme"})
    if pt_pct < 50:
        items.append(
            f"{i}. **[P3] Lens.org 特許エンリッチ** — {pt_pct:.0f}% → 目標 50%\n"
            "   - `python3 scripts/enrich_patents_lens.py`\n"
            "   - 無料登録: https://www.lens.org/ (tracking: d66a994c-7f38-4312-b533-9723d4959930)"
        )
        i += 1

    # 機能開発
    items.append(
        f"{i}. **[機能] フォーミュラ比較モード** — 保存済みフォーミュラのサイドバイサイド比較"
    )
    i += 1
    items.append(
        f"{i}. **[機能] フォーミュラ共有** — URLシェア or QRコード生成"
    )

    if not items:
        items.append("_すべての主要タスクが完了しています。_")

    text = _replace_section(text, "next-steps", "\n".join(items))

    project_file.write_text(text, encoding="utf-8")
    print("✅ project.md  動的セクション更新完了")


# ── ハッシュ ──────────────────────────────────────────────────────────────────

def compute_per_file_hashes() -> dict:
    return {
        str(p.relative_to(ROOT)): hashlib.md5(p.read_bytes()).hexdigest()[:12]
        for p in SOURCE_PATTERNS if p.exists()
    }


def read_embedded_file_hashes(progress_file: Path) -> Optional[dict]:
    FHASH_MARKER = "<!-- file-hashes:"
    if not progress_file.exists():
        return None
    for line in progress_file.read_text(encoding="utf-8").splitlines():
        if line.startswith(FHASH_MARKER):
            try:
                return json.loads(line.removeprefix(FHASH_MARKER).rstrip(" -->").strip())
            except Exception:
                return None
    return None


def check_stale() -> bool:
    out = DOCS_DIR / "progress.md"
    current_hash = compute_source_hash()
    stored_hash = read_embedded_hash(out)
    if stored_hash is None:
        print("⬜ docs/progress.md が存在しないか、ハッシュ未記録")
        return True
    if current_hash == stored_hash:
        mtime = datetime.fromtimestamp(out.stat().st_mtime, tz=timezone.utc)
        print(f"✅ docs/progress.md は最新です  ({mtime.strftime('%Y-%m-%d %H:%M UTC')})")
        return False
    current_files = compute_per_file_hashes()
    stored_files  = read_embedded_file_hashes(out) or {}
    changed  = [f"  • {k}" for k, v in current_files.items() if stored_files.get(k) != v]
    new_files = [f"  + {k}" for k in current_files if k not in stored_files]
    print("⚠️  docs/progress.md は古いです")
    for line in changed + new_files:
        print(line)
    print("   → python3 scripts/generate_docs.py で再生成してください")
    return True


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if "--check" in sys.argv:
        sys.exit(1 if check_stale() else 0)

    print("📄 docs/progress.md を生成中...")
    content = generate_progress()
    out = DOCS_DIR / "progress.md"
    out.write_text(content, encoding="utf-8")
    src_hash = compute_source_hash()
    print(f"✅ {out.relative_to(ROOT)}  hash={src_hash}  ({len(content.splitlines())} lines)")

    print("📄 project.md の動的セクションを更新中...")
    atoms_all: list[dict] = []
    for p in sorted(DATA_DIR.glob("*-atoms.json")):
        if not p.name.startswith(".") and not p.name.startswith("._"):
            atoms_all.extend(load_json(p))
    bonds_all = load_json(DATA_DIR / "bond-rules.json") if (DATA_DIR / "bond-rules.json").exists() else []
    tags_all  = load_json(DATA_DIR / "risk-tags.json")  if (DATA_DIR / "risk-tags.json").exists()  else []
    mvp_results_all = []
    for label, check_fn, detail in MVP_ITEMS:
        try:
            ok = check_fn()
        except Exception:
            ok = False
        mvp_results_all.append((label, ok, detail))
    update_project_md(atoms_all, bonds_all, tags_all, mvp_results_all)


if __name__ == "__main__":
    main()
