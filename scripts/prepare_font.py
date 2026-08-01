#!/usr/bin/env python3
"""把思源黑體的繁中字面抽成獨立字型檔。

**為什麼需要這一步**

`fonts-noto-cjk` 裝的是一個 collection 檔（`.ttc`），裡面依序放了 10 個字面：

    [0] Noto Sans CJK JP    [3] Noto Sans CJK TC
    [1] Noto Sans CJK KR    [4] Noto Sans CJK HK
    [2] Noto Sans CJK SC    ...

libass 無法選取 collection 內的子字面，永遠取 face[0]，也就是**日文字面**。
在 ASS 樣式裡寫 `Noto Sans CJK TC` 沒有用，fontconfig 一樣會把它解析回同一個
`.ttc` 然後拿到 face[0]。

實測結果：本片字幕與警語共 99 個相異漢字，其中 62 個（63%）的日文與繁中
字面不同 —— 包含 實、質、飲、時、無、豌、豆、藥、素、產、病，以及標點
「、。，」。日文標點在字身框裡靠左下，繁中置中，整行看起來都會不對。

**解法**

抽出 face[3]（繁中）另存成獨立字型檔，並把字型家族名改成專屬名稱，
fontconfig 就再也不可能把它跟系統的 `.ttc` 搞混。

用法：
    pip install fonttools
    python3 scripts/prepare_font.py

產出 fonts/CacaoSansTC-Regular.otf 與 -Bold.otf，`build.py` 會自動找到。
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"

FAMILY = "Cacao Sans TC"
WANT = "Noto Sans CJK TC"

SOURCES = [
    ("Regular", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ("Bold", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
]


def face_index(ttc_path: str, want: str) -> int:
    """找出 collection 裡家族名為 want 的字面編號。"""
    from fontTools.ttLib import TTCollection

    with TTCollection(ttc_path, lazy=True) as coll:
        for i, font in enumerate(coll.fonts):
            if font["name"].getDebugName(1) == want:
                return i
    raise SystemExit(f"{ttc_path} 裡找不到「{want}」字面")


def rename(font, style: str) -> None:
    """把字型家族名改成專屬名稱，避免 fontconfig 解析回系統的 .ttc。

    Noto 的 name table 對每個名稱都帶了數十種語系的記錄，只覆蓋英文那筆，
    fontconfig 仍會讀到殘留的舊家族名。所以先把相關的 nameID 全部清掉，
    再只寫回英文與 Mac 兩筆。
    """
    full = FAMILY if style == "Regular" else f"{FAMILY} {style}"
    ps = FAMILY.replace(" ", "") + f"-{style}"
    # 1 家族名、2 字重、4 完整名稱、6 PostScript 名稱、16/17 排版用家族／字重
    names = font["name"]
    names.names = [r for r in names.names if r.nameID not in (1, 2, 4, 6, 16, 17)]
    for plat, enc, lang in ((3, 1, 0x409), (1, 0, 0)):
        names.setName(FAMILY, 1, plat, enc, lang)
        names.setName(style, 2, plat, enc, lang)
        names.setName(full, 4, plat, enc, lang)
        names.setName(ps, 6, plat, enc, lang)


def main() -> int:
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("需要 fontTools：pip install fonttools", file=sys.stderr)
        return 1

    FONTS.mkdir(exist_ok=True)
    for style, src in SOURCES:
        if not pathlib.Path(src).exists():
            print(f"找不到 {src}，請先 apt-get install fonts-noto-cjk", file=sys.stderr)
            return 1

        idx = face_index(src, WANT)
        font = TTFont(src, fontNumber=idx)
        before = font["name"].getDebugName(1)
        rename(font, style)

        dest = FONTS / f"{FAMILY.replace(' ', '')}-{style}.otf"
        font.save(dest)
        print(f"{style:8} face[{idx}] {before} → {FAMILY} ({dest.stat().st_size/1e6:.1f} MB)")

    print(f"\n完成，字型在 {FONTS}。build.py 會自動使用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
