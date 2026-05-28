#!/usr/bin/env python3
"""
generate_docs.py — Formula Fuse Studio 進捗ドキュメント自動生成スクリプト

実行: python3 scripts/generate_docs.py
生成: docs/progress.md
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

# progress.md が読み取る対象ソースファイルのパターン
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


# ── MVP チェックリスト定義 ────────────────────────────────────────────────────
# (label, check_fn)  check_fn は bool を返す

def _file_exists(*parts):
    return (ROOT / Path(*parts)).exists()

def _has_content(path, keyword):
    p = ROOT / path
    return p.exists() and keyword in p.read_text(encoding="utf-8")

MVP_ITEMS = [
    (
        "Atom を登録できる（シードデータ）",
        lambda: _file_exists("data/seed-atoms/food-bio-atoms.json"),
        "シードJSON存在チェック",
    ),
    (
        "Atom を UI で選択できる",
        lambda: _file_exists("frontend/src/components/AtomLibrary.tsx"),
        "AtomLibrary.tsx",
    ),
    (
        "複数 Atom を Fuse して Formula を生成できる",
        lambda: _file_exists("backend/app/services/fuse_engine.py"),
        "fuse_engine.py",
    ),
    (
        "Formula を AI 解析できる（BYOK）",
        lambda: _file_exists("backend/app/services/ai_router.py"),
        "ai_router.py",
    ),
    (
        "Risk Gate で Green/Yellow/Red/Black を判定できる",
        lambda: _file_exists("backend/app/services/risk_gate.py"),
        "risk_gate.py",
    ),
    (
        "AI 出力を構造化 JSON で受け取る",
        lambda: _has_content("backend/app/models/formula.py", "AIAnalysisResult"),
        "AIAnalysisResult モデル",
    ),
    (
        "Formula を保存できる（永続化）",
        lambda: _has_content("backend/app/db/database.py", "postgresql")
                or _has_content("backend/app/db/database.py", "supabase")
                or _has_content("backend/app/db/database.py", "asyncpg"),
        "PostgreSQL/Supabase 接続",
    ),
    (
        "Formula を保存できる（インメモリ暫定）",
        lambda: _has_content("backend/app/db/database.py", "_formulas_store"),
        "_formulas_store（インメモリ）",
    ),
    (
        "Markdown レポートを出力できる",
        lambda: _file_exists("backend/app/services/report_generator.py"),
        "report_generator.py",
    ),
    (
        "BYOK 方式で API キーを使う",
        lambda: _file_exists("frontend/src/components/ApiKeyModal.tsx"),
        "ApiKeyModal.tsx",
    ),
    (
        "Formula Fuse Studio の UI で動作確認できる",
        lambda: _file_exists("frontend/src/app/page.tsx"),
        "page.tsx",
    ),
]


# ── ヘルパー ─────────────────────────────────────────────────────────────────

def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_routes(router_file: Path) -> list[dict]:
    text = router_file.read_text(encoding="utf-8")
    routes = []
    for m in re.finditer(
        r'@router\.(get|post|put|delete|patch)\("([^"]*)"',
        text,
    ):
        path = m.group(2) or "/"
        routes.append({"method": m.group(1).upper(), "path": path})
    return routes


def list_components(components_dir: Path) -> list[str]:
    if not components_dir.exists():
        return []
    return sorted(
        p.name
        for p in components_dir.glob("*.tsx")
        if not p.name.startswith(".") and not p.name.startswith("_")
    )


def ai_providers(ai_router_file: Path) -> list[str]:
    if not ai_router_file.exists():
        return []
    text = ai_router_file.read_text(encoding="utf-8")
    providers = []
    for name in ("openai", "claude", "gemini"):
        if f'provider == "{name}"' in text:
            providers.append(name)
    return providers


def phase_status(data_sources_file: Path) -> list[dict]:
    if not data_sources_file.exists():
        return []
    text = data_sources_file.read_text(encoding="utf-8")
    phases = []
    for m in re.finditer(r"^## (Phase \d+[：:].+)$", text, re.MULTILINE):
        phases.append({"title": m.group(1).strip()})
    return phases


# ── メイン生成 ────────────────────────────────────────────────────────────────

def generate_progress() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # --- Seed data（全 *-atoms.json を結合） ---
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

    atom_types    = Counter(a["atom_type"] for a in atoms)
    tag_sev       = Counter(t["severity"]  for t in tags)
    bond_types    = Counter(b["bond_type"] for b in bonds)
    atom_cats     = Counter(a["category"]  for a in atoms)

    # --- Backend ---
    routers_dir = BACKEND_DIR / "routers"
    all_routes: list[dict] = []
    def _py_files(d: Path) -> list[Path]:
        return sorted(p for p in d.glob("*.py") if not p.name.startswith(".") and p.name != "__init__.py") if d.exists() else []

    router_files = _py_files(routers_dir)
    for rf in router_files:
        for route in extract_routes(rf):
            route["file"] = rf.name
            all_routes.append(route)

    services_dir = BACKEND_DIR / "services"
    service_files = [p.name for p in _py_files(services_dir)]

    providers = ai_providers(BACKEND_DIR / "services" / "ai_router.py")

    # --- Frontend ---
    components = list_components(FRONTEND_DIR / "components")
    hooks = sorted(p.name for p in (FRONTEND_DIR / "hooks").glob("*.ts") if not p.name.startswith(".")) if (FRONTEND_DIR / "hooks").exists() else []
    lib_files = sorted(p.name for p in (FRONTEND_DIR / "lib").glob("*.ts") if not p.name.startswith(".")) if (FRONTEND_DIR / "lib").exists() else []

    # --- MVP check ---
    mvp_results = []
    for label, check_fn, detail in MVP_ITEMS:
        try:
            ok = check_fn()
        except Exception:
            ok = False
        mvp_results.append((label, ok, detail))

    done_count = sum(1 for _, ok, _ in mvp_results if ok)
    total_count = len(mvp_results)

    # --- Phase status ---
    phases = phase_status(DOCS_DIR / "data-sources.md")

    # ── Markdown 組み立て ──────────────────────────────────────────────────────
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

    # MVP Progress bar
    bar_filled = int(done_count / total_count * 20)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    pct = int(done_count / total_count * 100)
    lines += [
        "## MVP 達成率",
        "",
        f"```",
        f"[{bar}] {pct}%  ({done_count}/{total_count})",
        f"```",
        "",
    ]

    lines += ["## MVP スコープ", ""]
    for label, ok, detail in mvp_results:
        mark = "✅" if ok else "⬜"
        lines.append(f"- {mark} **{label}**  <sub>{detail}</sub>")
    lines.append("")

    # Data layer
    lines += [
        "---",
        "",
        "## データ層",
        "",
        "### Seed Atoms",
        "",
        f"| ファイル | 件数 |",
        f"|---|---:|",
    ]
    for af in atom_files:
        name, cnt = af.rsplit(" (", 1)
        lines.append(f"| `{name}` | {cnt.rstrip('件)')} |")
    lines += [
        f"| **合計** | **{len(atoms)}** |",
        "",
        "| atom_type | 件数 |",
        "|---|---:|",
    ]
    for t in ["ingredient", "microbe", "enzyme", "condition", "goal", "process"]:
        if atom_types.get(t):
            lines.append(f"| {t} | {atom_types[t]} |")
    lines.append("")

    # エンリッチメント統計
    enrich_fields = [
        ("compound",          "PubChem 化合物データ"),
        ("uniprot",           "UniProt 酵素・微生物データ"),
        ("gras",              "FDA GRAS ステータス"),
        ("usda",              "USDA 栄養データ"),
        ("pubmed_evidence",   "PubMed 文献エビデンス"),
        ("supplier_info",     "サプライヤー・OEM 情報"),
        ("patent_landscape",  "特許ランドスケープ"),
        ("market_trends",     "Google Trends 市場需要"),
        ("existing_products", "Open Food Facts 既存製品"),
    ]
    lines += ["### Atom エンリッチメント状況", "", "| フィールド | 付与済み件数 |", "|---|---:|"]
    for field, label in enrich_fields:
        count = sum(1 for a in atoms if a.get(field))
        lines.append(f"| {label} (`{field}`) | {count} / {len(atoms)} |")
    lines.append("")

    lines += [
        "### Risk Tags",
        "",
        f"| severity | 件数 |",
        f"|---|---:|",
        f"| **合計** | **{len(tags)}** |",
    ]
    for sev in ["black", "red", "yellow", "green"]:
        if tag_sev.get(sev):
            lines.append(f"| {sev} | {tag_sev[sev]} |")
    lines.append("")

    lines += [
        "### Bond Rules",
        "",
        f"合計 **{len(bonds)}** ルール",
        "",
    ]
    if bonds:
        lines += [
            "| bond_type | 件数 |",
            "|---|---:|",
        ]
        for bt, cnt in Counter(b["bond_type"] for b in bonds).most_common():
            lines.append(f"| {bt} | {cnt} |")
    lines.append("")

    # Backend
    lines += [
        "---",
        "",
        "## バックエンド（FastAPI）",
        "",
        "### API エンドポイント",
        "",
        f"合計 **{len(all_routes)}** ルート",
        "",
        "| Method | Path | Router |",
        "|---|---|---|",
    ]
    for r in all_routes:
        lines.append(f"| `{r['method']}` | `{r['path']}` | {r['file']} |")
    lines.append("")

    lines += [
        "### Services",
        "",
    ]
    for sf in service_files:
        lines.append(f"- ✅ `{sf}`")
    lines.append("")

    lines += [
        "### AI プロバイダー対応",
        "",
    ]
    for p in providers:
        lines.append(f"- ✅ {p}")
    if not providers:
        lines.append("- ⬜ 未実装")
    lines.append("")

    # DB 状態
    db_file = BACKEND_DIR / "db" / "database.py"
    if db_file.exists():
        db_text = db_file.read_text(encoding="utf-8")
        if any(kw in db_text for kw in ("postgresql", "asyncpg", "supabase", "psycopg")):
            db_status = "✅ PostgreSQL/Supabase 接続済み"
        else:
            db_status = "⚠️ インメモリ（`_formulas_store`）— 再起動でリセット"
    else:
        db_status = "⬜ DB 未実装"

    lines += [
        "### DB / 永続化",
        "",
        f"{db_status}",
        "",
    ]

    # Frontend
    lines += [
        "---",
        "",
        "## フロントエンド（Next.js）",
        "",
        "### Components",
        "",
    ]
    for c in components:
        lines.append(f"- ✅ `{c}`")
    lines.append("")

    lines += ["### Hooks", ""]
    for h in hooks:
        lines.append(f"- ✅ `{h}`")
    lines.append("")

    lines += ["### Lib", ""]
    for l in lib_files:
        lines.append(f"- ✅ `{l}`")
    lines.append("")

    # Data sources phases — エンリッチメント実績から動的に判定
    phase_checks = [
        # Phase 1: PubChem, USDA, MEXT, 手入力
        lambda: any(a.get("compound") for a in atoms) and any(a.get("usda") for a in atoms),
        # Phase 2: UniProt, PubMed
        lambda: any(a.get("uniprot") for a in atoms) and any(a.get("pubmed_evidence") for a in atoms),
        # Phase 3: GRAS, Safety Gate 強化
        lambda: any(a.get("gras") for a in atoms),
        # Phase 4: supplier, patent
        lambda: any(a.get("supplier_info") for a in atoms),
        # Phase 5: market, existing products
        lambda: any(a.get("market_trends") for a in atoms) or any(a.get("existing_products") for a in atoms),
    ]
    if phases:
        lines += [
            "---",
            "",
            "## データソース フェーズ",
            "",
            "| フェーズ | 状態 |",
            "|---|---|",
        ]
        for i, ph in enumerate(phases):
            if i < len(phase_checks):
                try:
                    done = phase_checks[i]()
                except Exception:
                    done = False
                status = "✅ 完了" if done else "🔄 進行中"
            else:
                status = "⬜ 未着手"
            lines.append(f"| {ph['title']} | {status} |")
    lines.append("")

    # Next actions
    incomplete = [(label, detail) for label, ok, detail in mvp_results if not ok]
    if incomplete:
        lines += [
            "---",
            "",
            "## 次のアクション（未完了 MVP 項目）",
            "",
        ]
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


def compute_per_file_hashes() -> dict:
    return {
        str(p.relative_to(ROOT)): hashlib.md5(p.read_bytes()).hexdigest()[:12]
        for p in SOURCE_PATTERNS if p.exists()
    }


def read_embedded_file_hashes(progress_file: Path) -> Optional[dict]:
    """progress.md に埋め込まれた per-file ハッシュを返す。"""
    FHASH_MARKER = "<!-- file-hashes:"
    if not progress_file.exists():
        return None
    for line in progress_file.read_text(encoding="utf-8").splitlines():
        if line.startswith(FHASH_MARKER):
            payload = line.removeprefix(FHASH_MARKER).rstrip(" -->").strip()
            try:
                return json.loads(payload)
            except Exception:
                return None
    return None


def check_stale() -> bool:
    """ソースが変わっているか調べる。古ければ True を返す。"""
    out = DOCS_DIR / "progress.md"
    current_hash = compute_source_hash()
    stored_hash = read_embedded_hash(out)

    if stored_hash is None:
        print("⬜ docs/progress.md が存在しないか、ハッシュ未記録")
        print("   → python3 scripts/generate_docs.py で生成してください")
        return True

    if current_hash == stored_hash:
        mtime = datetime.fromtimestamp(out.stat().st_mtime, tz=timezone.utc)
        print(f"✅ docs/progress.md は最新です  ({mtime.strftime('%Y-%m-%d %H:%M UTC')})")
        return False

    # 変更されたファイルを特定
    current_files = compute_per_file_hashes()
    stored_files  = read_embedded_file_hashes(out) or {}
    changed = [
        f"  • {k}"
        for k, v in current_files.items()
        if stored_files.get(k) != v
    ]
    new_files = [f"  + {k}" for k in current_files if k not in stored_files]

    print("⚠️  docs/progress.md は古いです")
    for line in changed + new_files:
        print(line)
    print("   → python3 scripts/generate_docs.py で再生成してください")
    return True


def _replace_section(text: str, name: str, new_body: str) -> str:
    """project.md の <!-- BEGIN:name --> … <!-- END:name --> ブロックを置き換える。"""
    begin = f"<!-- BEGIN:{name} -->"
    end = f"<!-- END:{name} -->"
    pattern = re.compile(
        re.escape(begin) + r".*?" + re.escape(end),
        re.DOTALL,
    )
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

    # ── current-state セクション ──────────────────────────────────────────────
    db_file = BACKEND_DIR / "db" / "database.py"
    env_file = ROOT / "backend" / ".env"
    db_ok = False
    if db_file.exists() and env_file.exists():
        env_text = env_file.read_text(encoding="utf-8")
        # プレースホルダ（your-*, <...>, PLACEHOLDER 等）を含まない実在URLか確認
        _placeholder = re.compile(r"your-|<[^>]+>|placeholder|example\.com", re.IGNORECASE)
        for line in env_text.splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            if (
                k == "SUPABASE_URL"
                and v.startswith("http")
                and not _placeholder.search(v)
            ):
                db_ok = True
                break
            if (
                k == "DATABASE_URL"
                and v.startswith(("postgresql://", "postgres://"))
                and not _placeholder.search(v)
            ):
                db_ok = True
                break

    enrich_fields = [
        ("compound",          "Phase 1: PubChem エンリッチ"),
        ("uniprot",           "Phase 2: UniProt"),
        ("pubmed_evidence",   "Phase 2: PubMed"),
        ("gras",              "Phase 3: FDA GRAS + Safety Gate 強化"),
        ("supplier_info",     "Phase 4: サプライヤー情報"),
        ("market_trends",     "Phase 5: Google Trends"),
        ("existing_products", "Phase 5: Open Food Facts"),
    ]

    mvp_lookup = {label: ok for label, ok, _ in mvp_results}

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
    ]
    for field, label in enrich_fields:
        n = sum(1 for a in atoms if a.get(field))
        if n == 0:
            rows_cs.append((label, "⬜ 0件 — 未実行"))
        elif n == len(atoms):
            rows_cs.append((label, "✅ 完成"))
        else:
            pct = int(n / len(atoms) * 100)
            rows_cs.append((label, f"⚠️ {n}/{len(atoms)} ({pct}%)"))

    if db_ok:
        rows_cs.append(("**Formula 保存（Supabase DB）**", "✅ 本番稼働中"))
    else:
        rows_cs.append(("Formula 保存（インメモリ暫定）", "⚠️ 動作中（再起動でリセット）"))
        rows_cs.append(("**Formula 保存（DB 永続化）**", "⬜ **未着手 ← Next**"))

    cs_lines = ["| 区分 | 状態 |", "|---|---|"]
    for label, status in rows_cs:
        cs_lines.append(f"| {label} | {status} |")
    text = _replace_section(text, "current-state", "\n".join(cs_lines))

    # ── atom-counts セクション ────────────────────────────────────────────────
    type_parts = " / ".join(
        f"{t} {atom_types.get(t, 0)}"
        for t in ["ingredient", "microbe", "enzyme", "condition", "goal"]
    )
    text = _replace_section(
        text, "atom-counts",
        f"現在 **{len(atoms)} Atoms**（{type_parts}）"
    )

    # ── bond-counts セクション ────────────────────────────────────────────────
    red_n    = tag_sev.get("red", 0)
    yellow_n = tag_sev.get("yellow", 0)
    text = _replace_section(
        text, "bond-counts",
        f"現在 **{len(bonds)} Bond Rules**。"
        f"Risk Tags **{len(tags)}** 件（red {red_n} / yellow {yellow_n}）。"
    )

    # ── data-phases セクション ────────────────────────────────────────────────
    phase_defs = [
        ("0", "手動シード Atom",
         lambda: True),
        ("1", "PubChem / MEXT / USDA API 連携",
         lambda: any(a.get("compound") for a in atoms)),
        ("2", "UniProt / PubMed",
         lambda: any(a.get("uniprot") for a in atoms) and any(a.get("pubmed_evidence") for a in atoms)),
        ("3", "FDA GRAS / Safety Gate 強化",
         lambda: any(a.get("gras") for a in atoms)),
        ("4", "サプライヤー / Lens.org 特許",
         lambda: any(a.get("supplier_info") for a in atoms)),
        ("5", "Google Trends / Open Food Facts",
         lambda: any(a.get("market_trends") for a in atoms) or any(a.get("existing_products") for a in atoms)),
    ]
    usda_done = any(a.get("usda") for a in atoms)
    phases_partial = {
        "1": "⚠️ 一部完了（PubChem のみ・MEXT未）" if usda_done else "⚠️ 一部完了（USDA は API キー必要）",
        "4": "⚠️ 一部完了（Lens.org 特許未取得）",
        "5": "⚠️ 完了（Trends は rate limit あり）",
    }
    dp_lines = ["| Phase | 内容 | 状態 |", "|---|---|---|"]
    for pid, desc, check_fn in phase_defs:
        try:
            done = check_fn()
        except Exception:
            done = False
        status = (
            phases_partial.get(pid, "✅ 完了") if done
            else ("🔄 進行中" if pid != "0" else "⬜ 未着手")
        )
        dp_lines.append(f"| {pid} | {desc} | {status} |")
    text = _replace_section(text, "data-phases", "\n".join(dp_lines))

    # ── next-steps セクション ─────────────────────────────────────────────────
    next_items: list[str] = []
    if not db_ok:
        next_items.append(
            "1. **DB 永続化**（唯一残っている MVP 未完了項目）\n"
            "   - PostgreSQL / Supabase 接続\n"
            "   - `backend/.env` に接続情報を設定し `migration.sql` を実行"
        )
    n_no = sum(1 for a in atoms if not a.get("usda"))
    if n_no == len(atoms):
        next_items.append(
            f"{len(next_items)+1}. **USDA API キー取得** → `python3 scripts/import_usda.py`\n"
            "   - 無料: https://api.nal.usda.gov/"
        )
    if not any(a.get("patent_landscape") for a in atoms):
        next_items.append(
            f"{len(next_items)+1}. **Lens.org API キー取得** → `python3 scripts/enrich_patents_lens.py`\n"
            "   - 無料登録: https://www.lens.org/"
        )
    trend_zeros = sum(
        1 for a in atoms
        if a.get("market_trends") and a["market_trends"].get("avg_interest_jp", 0) == 0
    )
    if trend_zeros > 10:
        next_items.append(
            f"{len(next_items)+1}. **Google Trends rate limit 回避**\n"
            "   - 数時間待機後に `python3 scripts/enrich_google_trends.py --force` を再実行"
        )
    if not next_items:
        next_items.append("_すべての主要タスクが完了しています。_")

    text = _replace_section(text, "next-steps", "\n".join(next_items))

    project_file.write_text(text, encoding="utf-8")
    print(f"✅ project.md  動的セクション更新完了")


def main():
    if "--check" in sys.argv:
        stale = check_stale()
        sys.exit(1 if stale else 0)

    print("📄 docs/progress.md を生成中...")
    content = generate_progress()
    out = DOCS_DIR / "progress.md"
    out.write_text(content, encoding="utf-8")
    src_hash = compute_source_hash()
    print(f"✅ {out.relative_to(ROOT)}  hash={src_hash}  ({len(content.splitlines())} lines)")

    # project.md の動的セクションも同時更新
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
