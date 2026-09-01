#!/usr/bin/env python3
"""把 100 種喝法清單（markdown）轉成機器可讀的 recipes.json。

唯一的內容來源是 docs/100-ways/01-100種喝法清單.md，改配方只動那份，
然後跑這支腳本重新產生 JSON。不要手動編輯 recipes.json。

用法：
    python3 scripts/recipes.py            # 產生 recipes.json
    python3 scripts/recipes.py --check    # 只驗證，不寫檔（CI 用）
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "100-ways" / "01-100種喝法清單.md"
OUT = ROOT / "docs" / "100-ways" / "recipes.json"

# 口味簡稱 → 商品事實。取自 Shopify 商品頁，勿憑印象改。
FLAVORS = {
    "拿鐵":   {"name": "拿鐵風味",         "sku_1": "VG00L1", "sku_12": "VG00L2", "protein_g": 24.0, "warning": None},
    "紅茶":   {"name": "植感奶霧紅茶",     "sku_1": "VG00T1", "sku_12": "VG00T2", "protein_g": 24.1, "warning": None},
    "可可":   {"name": "植感醇黑可可",     "sku_1": "VG00C1", "sku_12": "VG00C2", "protein_g": 24.0, "warning": "Q10"},
    "穀物":   {"name": "綜合穀物",         "sku_1": "VG00G1", "sku_12": "VG00G2", "protein_g": 24.6, "warning": None},
    "開心果": {"name": "開心果可可",       "sku_1": "VG00P1", "sku_12": "VG00P2", "protein_g": 24.0, "warning": "GABA"},
    "抹茶":   {"name": "靜岡抹茶燕麥風味", "sku_1": "VG00M1", "sku_12": "VG00M2", "protein_g": 23.0, "warning": None},
    "香蕉":   {"name": "香蕉牛奶風味",     "sku_1": "VG00B1", "sku_12": "VG00B2", "protein_g": 26.2, "warning": "GABA"},
    "芝麻":   {"name": "黑芝麻牛奶風味",   "sku_1": "VG00S1", "sku_12": "VG00S2", "protein_g": 22.0, "warning": "GABA"},
}

WARNING_TEXT = {
    "Q10": "本產品含輔酵素Q10，十五歲以下孩童、懷孕或哺乳期間婦女，及服用抗凝血藥品之病患不宜食用。",
    "GABA": "本產品含有GABA，使用本產品應避免同時飲酒或服用降血壓、鎮靜及癲癇等藥物；孕婦、授乳者、嬰幼兒，須諮詢醫師方可使用。",
}

# 食安提醒，對照 03-廣告用字與警語.md 第 5 節
FOOD_SAFETY = {
    "當日飲用完畢": {8, 43, 59, 61, 62, 63, 64, 69, 94} | set(range(41, 51)),
    "冷藏保存，3日內食用完畢": {65, 69, 71, 75, 76, 77, 79, 80},
    "泡好後建議2小時內飲用完畢": {90},
    "水溫勿超過80°C": {56} | set(range(81, 91)),
    "請勿密封搖晃": {15, 54},
}

ROW = re.compile(r"^\|\s*(\d{3})\s*\|(.+)\|\s*$")
HEADING = re.compile(r"^## (S\d+) (.+?) `#(\d{3})\s*[–-]\s*#(\d{3})`\s*$")


def parse():
    series = {}
    recipes = []
    current = None

    for lineno, raw in enumerate(SRC.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip()

        m = HEADING.match(line)
        if m:
            key, title, lo, hi = m.groups()
            current = key
            series[key] = {"id": key, "title": title.strip(), "from": int(lo), "to": int(hi)}
            continue

        m = ROW.match(line)
        if not m:
            continue
        if current is None:
            raise SystemExit(f"{SRC.name}:{lineno} 配方列出現在任何系列標題之前")

        rid = int(m.group(1))
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) != 4:
            raise SystemExit(
                f"{SRC.name}:{lineno} 第 {rid} 列有 {len(cells) + 1} 欄，應為 5 欄"
                "（# | 名稱 | 口味 | 配方與做法 | 影片鉤子）"
            )

        name, flavor_cell, method, hook = cells
        flavors = [f.strip() for f in flavor_cell.split("+")]

        warnings, resolved = [], []
        for f in flavors:
            if f == "任一":
                resolved.append({"key": "任一", "note": "拍攝時實際選用的口味，警語跟著該口味走"})
                continue
            if f not in FLAVORS:
                raise SystemExit(f"{SRC.name}:{lineno} 第 {rid} 列的口味「{f}」不在對照表中")
            info = FLAVORS[f]
            resolved.append({"key": f, **{k: v for k, v in info.items() if k != "warning"}})
            if info["warning"] and info["warning"] not in warnings:
                warnings.append(info["warning"])

        recipes.append({
            "id": rid,
            "code": f"#{rid:03d}",
            "series": current,
            "name": name,
            "flavors": resolved,
            "method": method,
            "hook": hook,
            "warnings": [{"kind": w, "text": WARNING_TEXT[w]} for w in warnings],
            "food_safety": sorted(t for t, ids in FOOD_SAFETY.items() if rid in ids),
            "slug": f"100ways_{current}_{rid:03d}_{name}",
        })

    return series, recipes


def validate(series, recipes):
    errors = []
    ids = [r["id"] for r in recipes]

    if len(ids) != 100:
        errors.append(f"共解析到 {len(ids)} 筆配方，應為 100 筆")
    if sorted(ids) != list(range(1, 101)):
        missing = sorted(set(range(1, 101)) - set(ids))
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if missing:
            errors.append(f"缺少編號：{missing}")
        if dupes:
            errors.append(f"重複編號：{dupes}")
    if len(series) != 10:
        errors.append(f"共解析到 {len(series)} 個系列，應為 10 個")

    for r in recipes:
        s = series[r["series"]]
        if not s["from"] <= r["id"] <= s["to"]:
            errors.append(f"#{r['id']:03d} 落在 {s['id']} 的宣告範圍 {s['from']}–{s['to']} 之外")

    return errors


def main():
    check_only = "--check" in sys.argv
    series, recipes = parse()

    errors = validate(series, recipes)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return 1

    doc = {
        "_comment": "由 scripts/recipes.py 從 01-100種喝法清單.md 產生，請勿手動編輯。",
        "source": str(SRC.relative_to(ROOT)),
        "sachet_g": 35,
        "warning_text": WARNING_TEXT,
        "series": list(series.values()),
        "recipes": recipes,
    }

    with_warning = sum(1 for r in recipes if r["warnings"])
    print(f"{len(recipes)} 筆配方、{len(series)} 個系列，其中 {with_warning} 筆需帶法定警語")

    if check_only:
        print("--check：驗證通過，未寫檔")
        return 0

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已寫入 {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
