# Safety Gate — 仕様書

## 概要

Safety GateはFormulaのリスクを4段階で判定し、利用可能なアクションを制御するシステム。

AIの出力より安全ゲートを優先する。AIが「安全」と言ってもRisk Tagがある場合はGateが上書きする。

## 判定基準

### Green ✅

商品化検討OK。重大な安全性リスクが低い。

**条件:**
- Risk Tagにアレルゲン・毒性・医薬品境界・規制引っかかりが含まれない
- 全Atomが食品グレード想定
- 根拠が十分またはリスクが低い

**表示可能アクション:**
- 実験計画生成
- 先行技術調査ガイド
- 専門家レビュー依頼先（オプション）
- 原材料候補表示
- 加工方法候補表示
- 商品化方向生成
- Patent Briefへの移行
- Markdownレポート出力

### Yellow ⚠️

専門家確認が必要。アレルゲン・根拠不足・表示リスク・研究段階のもの。

**条件（いずれか）:**
- `wheat_allergen` / `milk_allergen` / `soy_allergen` / `egg_allergen` / `nut_allergen` のいずれかを含む
- `celiac_claim_risk` / `claim_requires_evidence` / `insufficient_evidence` を含む
- `dose_review_required` を含む
- Evidence Level がE1以下

**表示可能アクション:**
- 研究仮説・実験計画
- 注意事項の表示
- 専門家レビュー導線（必須）

**制限:**
- 確定的な効果表現を禁止
- 原材料購入導線は専門家確認後
- 商品化表現は構わない（安全な例示のみ）

### Red 🔴

危険・規制・医薬品境界の可能性。購入・加工・商品化導線を制限。

**条件（いずれか）:**
- `toxicology_review_required` を含む
- `pharmaceutical_borderline` を含む
- `manufacturing_safety_review` を含む
- `fermentation_contamination_risk` + `microbial_safety_review` の両方を含む

**表示可能アクション:**
- 危険警告
- 専門家相談
- 追加調査項目

**制限:**
- 原材料購入導線を出さない
- 加工方法を出さない
- 商品化提案を出さない
- 販売導線を出さない

### Black ⛔

明らかに危険・違法・有害用途。ブロック。

**条件:**
- AIがBlackと判定した場合
- `expert_review_required` + `pharmaceutical_borderline` + `toxicology_review_required` が全て揃う場合
- 明らかに有害・兵器・化学兵器・自傷につながる組み合わせ

**表示:**
- ブロック画面のみ
- 安全な代替方向のみ表示

---

## Safety Gate出力フォーマット

```json
{
  "safety_status": "Green | Yellow | Red | Black",
  "blocking_reasons": [],
  "risk_tags_detected": [],
  "allowed_actions": [
    "experiment_plan",
    "patent_brief",
    "productize",
    "supplier",
    "report"
  ],
  "restricted_actions": [],
  "required_expert_reviews": [],
  "safe_alternative_direction": []
}
```

## アクションID定義

| action_id | 説明 |
|---|---|
| `experiment_plan` | 実験計画の生成 |
| `prior_art_search` | 先行技術調査ガイド |
| `expert_review` | 専門家レビュー依頼 |
| `ingredient_sourcing` | 原材料候補表示 |
| `process_direction` | 加工方法候補表示 |
| `productize` | 商品化提案 |
| `patent_brief` | Patent Brief生成 |
| `supplier_oem` | OEM・サプライヤー検索 |
| `report` | Markdownレポート出力 |

## ルール適用順序

1. Black判定チェック（最優先）
2. Red判定チェック
3. Yellow判定チェック  
4. 全てクリア → Green

一度でもBlack/Redに該当すればそれ以上チェックせず確定する。
