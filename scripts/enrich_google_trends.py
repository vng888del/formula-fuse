#!/usr/bin/env python3
"""
enrich_google_trends.py — Google Trends で Atom の市場需要シグナルを付与

【概要】
pytrends (非公式 Google Trends API) を使って ingredient / goal Atom に
市場トレンドデータを付与する（atom 内 "market_trends" キー）:

  market_trends: {
    "keyword"          : 検索キーワード
    "geo"              : 地域コード (JP / US / "")
    "timeframe"        : 検索期間
    "avg_interest_jp"  : 直近12ヶ月 日本平均関心度 (0–100)
    "avg_interest_us"  : 直近12ヶ月 US平均関心度 (0–100)
    "avg_interest_ww"  : 直近12ヶ月 全世界平均関心度 (0–100)
    "trend_direction"  : "rising" | "stable" | "declining"
    "peak_month_jp"    : 日本でピークだった月 (YYYY-MM)
    "retrieved_at"     : 取得日時 (ISO 8601)
  }

【依存ライブラリ】
  pip install pytrends pandas

【実行】
  python3 scripts/enrich_google_trends.py
  python3 scripts/enrich_google_trends.py --dry-run
  python3 scripts/enrich_google_trends.py --atom-id atom_gaba

【注意】
  pytrends は Google の非公式 API です。
  レートリミット (429) が発生した場合は自動的に 60 秒待機します。
  1 リクエストにつき最大 5 キーワードまで比較できるため、バッチ処理します。
"""

import json
import time
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

ROOT = Path(__file__).parent.parent
ATOMS_FILE = ROOT / "data" / "seed-atoms" / "food-bio-atoms.json"

TARGET_TYPES = {"ingredient", "goal"}

# 検索キーワードのカスタマイズ（日本語検索の方が JP 精度が高い場合）
KEYWORD_OVERRIDES: dict[str, str] = {
    "atom_gaba":            "GABA サプリ",
    "atom_theanine":        "テアニン サプリ",
    "atom_curcumin":        "ウコン クルクミン",
    "atom_magnesium":       "マグネシウム サプリ",
    "atom_vitamin_c":       "ビタミンC サプリ",
    "atom_zinc":            "亜鉛 サプリ",
    "atom_iron":            "鉄分 サプリ",
    "atom_dha_epa":         "DHA EPA サプリ",
    "atom_coq10":           "コエンザイムQ10",
    "atom_astaxanthin":     "アスタキサンチン",
    "atom_hyaluronic_acid": "ヒアルロン酸 サプリ",
    "atom_collagen":        "コラーゲン サプリ",
    "atom_inulin":          "イヌリン 食物繊維",
    "atom_lactobacillus":   "乳酸菌 サプリ",
    "atom_bifidobacterium": "ビフィズス菌 サプリ",
    "atom_green_tea":       "緑茶 カテキン",
    "atom_kurozu":          "黒酢 サプリ",
    "atom_germinated_brown_rice": "発芽玄米 GABA",
    "atom_whey_protein":    "ホエイプロテイン",
    "atom_caffeine":        "カフェイン サプリ",
    # Goals
    "goal_digestion":        "消化 サプリ 腸活",
    "goal_gut":              "腸活 プロバイオティクス",
    "goal_sleep":            "睡眠 サプリ",
    "goal_antioxidant":      "抗酸化 サプリ",
    "goal_immune":           "免疫 サプリ",
    "goal_sports":           "スポーツ サプリ プロテイン",
    "goal_skin":             "美肌 サプリ コラーゲン",
    "goal_bone":             "骨 関節 サプリ",
}

TIMEFRAME = "today 12-m"


def get_keyword(atom: dict) -> str:
    atom_id = atom["atom_id"]
    if atom_id in KEYWORD_OVERRIDES:
        return KEYWORD_OVERRIDES[atom_id]
    name = atom["name_en"].split("(")[0].split("/")[0].strip()
    return name


def fetch_trends(keywords: list[str]) -> Optional[dict]:
    """
    pytrends で JP・US・WW の関心度を取得する。
    keywords は最大 5 件。
    戻り値: {keyword: {jp, us, ww 平均関心度, trend_direction, peak_month_jp}}
    """
    try:
        from pytrends.request import TrendReq
        import pandas as pd
    except ImportError:
        print("❌ pytrends / pandas が必要: pip install pytrends pandas")
        sys.exit(1)

    results = {}

    def _fetch_geo(geo: str) -> Optional[object]:
        pr = TrendReq(hl="ja-JP", tz=540, timeout=(15, 30))
        try:
            pr.build_payload(keywords, cat=0, timeframe=TIMEFRAME, geo=geo)
            df = pr.interest_over_time()
            if df is None or df.empty:
                return None
            if "isPartial" in df.columns:
                df = df[~df["isPartial"]]
            return df
        except Exception as e:
            if "429" in str(e) or "Too Many" in str(e):
                print("⚠️  Rate limit, wait 60s...", flush=True)
                time.sleep(60)
            return None

    df_jp = _fetch_geo("JP")
    time.sleep(2)
    df_us = _fetch_geo("US")
    time.sleep(2)
    df_ww = _fetch_geo("")

    for kw in keywords:
        avg_jp = avg_us = avg_ww = 0
        peak_month_jp = ""
        trend_direction = "stable"

        if df_jp is not None and kw in df_jp.columns:
            series_jp = df_jp[kw].astype(float)
            avg_jp = int(series_jp.mean())
            # ピーク月
            if avg_jp > 0:
                peak_idx = series_jp.idxmax()
                peak_month_jp = str(peak_idx)[:7]
            # トレンド方向（後半 vs 前半の平均比較）
            n = len(series_jp)
            if n >= 4:
                first_half = series_jp.iloc[:n//2].mean()
                second_half = series_jp.iloc[n//2:].mean()
                if second_half > first_half * 1.15:
                    trend_direction = "rising"
                elif second_half < first_half * 0.85:
                    trend_direction = "declining"

        if df_us is not None and kw in df_us.columns:
            avg_us = int(df_us[kw].astype(float).mean())

        if df_ww is not None and kw in df_ww.columns:
            avg_ww = int(df_ww[kw].astype(float).mean())

        results[kw] = {
            "avg_interest_jp": avg_jp,
            "avg_interest_us": avg_us,
            "avg_interest_ww": avg_ww,
            "trend_direction": trend_direction,
            "peak_month_jp":   peak_month_jp,
        }

    return results


def main():
    parser = argparse.ArgumentParser(description="Google Trends 市場需要シグナルを Atom に付与")
    parser.add_argument("--dry-run", action="store_true", help="対象一覧とクエリのみ表示")
    parser.add_argument("--atom-id", help="特定の atom_id のみ処理")
    parser.add_argument("--force", action="store_true", help="既に market_trends がある Atom も再取得")
    args = parser.parse_args()

    atoms = json.loads(ATOMS_FILE.read_text(encoding="utf-8"))

    targets = [
        a for a in atoms
        if a.get("atom_type") in TARGET_TYPES
        and (args.force or "market_trends" not in a)
    ]

    if args.atom_id:
        targets = [a for a in targets if a.get("atom_id") == args.atom_id]

    print(f"📈 Google Trends 対象: {len(targets)} Atom")

    if args.dry_run:
        for a in targets:
            kw = get_keyword(a)
            print(f"  • {a['atom_id']:35s}  keyword: 「{kw}」")
        return

    # バックアップ
    bak = ATOMS_FILE.with_suffix(".json.bak")
    bak.write_bytes(ATOMS_FILE.read_bytes())
    print(f"💾 バックアップ: {bak.name}")

    atom_index = {a["atom_id"]: a for a in atoms}
    hit = 0
    miss = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    # pytrends は 5 件ずつバッチ処理
    batch_size = 5
    i = 0
    while i < len(targets):
        batch = targets[i:i + batch_size]
        keywords = [get_keyword(a) for a in batch]

        print(f"\n[{i+1}–{min(i+batch_size, len(targets))}/{len(targets)}] "
              f"fetching: {keywords}", flush=True)

        trend_data = fetch_trends(keywords)

        for j, target in enumerate(batch):
            kw = keywords[j]
            if trend_data and kw in trend_data:
                td = trend_data[kw]
                atom_index[target["atom_id"]]["market_trends"] = {
                    "keyword":         kw,
                    "geo":             "JP+US+WW",
                    "timeframe":       TIMEFRAME,
                    **td,
                    "retrieved_at":    now_iso,
                }
                jp  = td["avg_interest_jp"]
                us  = td["avg_interest_us"]
                dir_icon = {"rising": "📈", "stable": "➡️", "declining": "📉"}.get(td["trend_direction"], "")
                print(f"  ✅  {dir_icon} JP={jp:3d}  US={us:3d}  {kw}")
                hit += 1
            else:
                print(f"  —  miss: {kw}")
                miss += 1

        i += batch_size
        if i < len(targets):
            print("   ⏳ 次のバッチまで 15 秒待機...", flush=True)
            time.sleep(15)

    # 上書き保存
    ATOMS_FILE.write_text(
        json.dumps(list(atom_index.values()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n✅ 完了  hit={hit}  miss={miss}")
    print(f"💾 保存: {ATOMS_FILE}")
    print("\n次のステップ:")
    print("  python3 scripts/generate_docs.py")


if __name__ == "__main__":
    main()
