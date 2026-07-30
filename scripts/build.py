#!/usr/bin/env python3
"""依 edl.json 組出成品。

    python3 scripts/build.py                 # 輸出 9:16 與 4:5 兩個版本
    python3 scripts/build.py --aspect 9:16   # 只出直式
    python3 scripts/build.py --draft         # 低畫質快速預覽

edl.json 是唯一的剪輯決策來源 — 改剪點、改字幕、換配樂都只動那個檔案，
不要改這支腳本。
"""

import argparse
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _ffmpeg import FFMPEG  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
OUT = ROOT / "out"

# 字幕字型候選，由上往下找第一個裝得到的。(檔案路徑, ASS 用的字型家族名)
# 家族名不能從檔名推 —— .ttc 一個檔含多個家族，libass 是靠家族名比對的。
FONT_CANDIDATES = [
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "Noto Sans CJK TC"),  # 思源黑體
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "WenQuanYi Zen Hei"),
]
ACCENT = "&H004AB2E8&"  # 可可金 #E8B24A（ASS 為 BGR 序）— 換成品牌主色

# 各比例的輸出尺寸與字幕安全邊距（自畫面底部起算）
ASPECTS = {
    "9:16": {"w": 1080, "h": 1920, "margin_v": 520},
    "4:5": {"w": 1080, "h": 1350, "margin_v": 320},
    "1:1": {"w": 1080, "h": 1080, "margin_v": 240},
}


def ass_escape(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    # edl.json 裡打真正的換行，轉成 ASS 的硬斷行。樣式是 WrapStyle 2（不自動斷行），
    # 長句不手動斷會直接衝出畫面。
    return escaped.replace("\n", "\\N")


def ass_time(seconds: float) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def build_ass(edl: dict, spec: dict, font: str, path: pathlib.Path) -> None:
    """把 edl 的字幕段落寫成 ASS。**粗體標記** 會放大並套上重音色。"""
    size = round(spec["h"] * 0.038)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {spec['w']}
PlayResY: {spec['h']}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{font},{size},&H00FFFFFF&,&H00000000&,&H80000000&,-1,0,1,{max(size // 12, 3)},2,2,60,60,{spec['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for cue in edl["subtitles"]:
        text = ass_escape(cue["text"])
        # **重點** → 放大 1.4 倍並改色，收回時還原
        while "**" in text:
            text = text.replace("**", f"{{\\fs{round(size * 1.4)}\\c{ACCENT}}}", 1)
            text = text.replace("**", f"{{\\fs{size}\\c&H00FFFFFF&}}", 1)
        lines.append(
            f"Dialogue: 0,{ass_time(cue['start'])},{ass_time(cue['end'])},"
            f"Main,,0,0,0,,{text}"
        )

    if note := edl.get("disclaimer"):
        # 警語疊在主字幕上方一行 — 放到字幕下方會落進 IG 說明文字／FB CTA 的遮蔽區
        small = round(size * 0.30)
        lines.append(
            f"Dialogue: 0,{ass_time(note['start'])},{ass_time(note['end'])},"
            f"Main,,0,0,{spec['margin_v'] + round(size * 1.8)},,"
            f"{{\\fs{small}\\c&H00E0E0E0&}}{ass_escape(note['text'])}"
        )

    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def build_filters(edl: dict, spec: dict, ass_path: pathlib.Path, font_dir: str) -> tuple[str, str]:
    """組出 filter_complex，回傳 (filtergraph, 音訊輸出標籤)。"""
    w, h, fps = spec["w"], spec["h"], edl.get("fps", 30)
    parts, vlabels, alabels = [], [], []

    for i, seg in enumerate(edl["segments"]):
        speed = seg.get("speed", 1.0)
        parts.append(
            f"[{i}:v]trim=start={seg['in']}:end={seg['out']},"
            f"setpts=(PTS-STARTPTS)/{speed},"
            f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},fps={fps},setsar=1[v{i}]"
        )
        vlabels.append(f"[v{i}]")

        if seg.get("has_audio", True):
            # atempo 單次僅支援 0.5–2.0，超出範圍就串接
            tempo, chain = speed, []
            while tempo > 2.0:
                chain.append("atempo=2.0")
                tempo /= 2.0
            while tempo < 0.5:
                chain.append("atempo=0.5")
                tempo /= 0.5
            chain.append(f"atempo={tempo:.4f}")
            parts.append(
                f"[{i}:a]atrim=start={seg['in']}:end={seg['out']},"
                f"asetpts=PTS-STARTPTS,{','.join(chain)},"
                f"aformat=sample_rates=48000:channel_layouts=stereo[a{i}]"
            )
        else:
            dur = (seg["out"] - seg["in"]) / speed
            parts.append(
                f"anullsrc=r=48000:cl=stereo,atrim=duration={dur:.3f}[a{i}]"
            )
        alabels.append(f"[a{i}]")

    n = len(edl["segments"])
    pairs = "".join(v + a for v, a in zip(vlabels, alabels))
    parts.append(f"{pairs}concat=n={n}:v=1:a=1[vcat][araw]")

    escaped = str(ass_path).replace("\\", "/").replace(":", r"\:")
    parts.append(f"[vcat]subtitles='{escaped}':fontsdir='{font_dir}'[vout]")

    audio = edl.get("audio", {})
    parts.append(f"[araw]volume={audio.get('original_gain', 0.35)}[aorig]")

    extra = n  # 額外音軌的 input 索引接在影片之後
    mix_inputs = ["[aorig]"]
    if audio.get("voiceover"):
        parts.append(f"[{extra}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                     f"volume={audio.get('voiceover_gain', 1.0)}[avo]")
        mix_inputs.append("[avo]")
        extra += 1
    if audio.get("bgm"):
        parts.append(
            f"[{extra}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
            f"volume={audio.get('bgm_gain', 0.18)}[abgm_raw]"
        )
        if audio.get("voiceover") and audio.get("duck", True):
            # 旁白進來時把配樂壓下去，這是旁白聽不聽得清楚的關鍵
            parts.append("[avo]asplit=2[avo_mix][avo_key]")
            parts.append(
                "[abgm_raw][avo_key]sidechaincompress="
                "threshold=0.05:ratio=8:attack=20:release=400[abgm]"
            )
            mix_inputs = ["[aorig]", "[avo_mix]", "[abgm]"]
        else:
            parts.append("[abgm_raw]anull[abgm]")
            mix_inputs.append("[abgm]")

    if len(mix_inputs) > 1:
        parts.append(
            f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:"
            f"duration=first:normalize=0,alimiter=limit=0.95[aout]"
        )
    else:
        parts.append("[aorig]anull[aout]")

    return ";".join(parts), "[aout]"


def pick_font(path: str | None, family: str | None) -> tuple[str, str]:
    """回傳 (字型檔路徑, ASS 家族名)。沒指定就用候選清單裡第一個裝得到的。"""
    if path:
        return path, family or pathlib.Path(path).stem
    for cand_path, cand_family in FONT_CANDIDATES:
        if pathlib.Path(cand_path).exists():
            return cand_path, family or cand_family
    raise SystemExit("找不到任何中文字型，請用 --font 指定字型檔")


def render(edl: dict, aspect: str, draft: bool, font: str, family: str) -> pathlib.Path:
    spec = ASPECTS[aspect]
    OUT.mkdir(exist_ok=True)
    slug = aspect.replace(":", "x")
    ass_path = OUT / f"subs_{slug}.ass"
    build_ass(edl, spec, family, ass_path)

    cmd = [FFMPEG, "-nostdin", "-y"]
    for seg in edl["segments"]:
        cmd += ["-i", str(RAW / seg["src"])]
    audio = edl.get("audio", {})
    if audio.get("voiceover"):
        cmd += ["-i", str(ROOT / audio["voiceover"])]
    if audio.get("bgm"):
        cmd += ["-stream_loop", "-1", "-i", str(ROOT / audio["bgm"])]

    graph, alabel = build_filters(edl, spec, ass_path, str(pathlib.Path(font).parent))
    dest = OUT / f"cacao_30s_{slug}{'_draft' if draft else ''}.mp4"
    # 素材混了 29.97 與 30 fps，串接時會多進位一兩格。用 EDL 算出的總長硬性截斷，
    # 確保成品長度與剪輯決策完全一致。
    total = sum((s["out"] - s["in"]) / s.get("speed", 1.0) for s in edl["segments"])
    cmd += [
        "-filter_complex", graph,
        "-map", "[vout]", "-map", alabel,
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-preset", "veryfast" if draft else "slow",
        "-crf", "30" if draft else "20",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(dest),
    ]

    print(f"→ 輸出 {aspect}：{dest.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-3000:], file=sys.stderr)
        raise SystemExit(f"ffmpeg 失敗（{aspect}）")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aspect", choices=list(ASPECTS), action="append")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--font", help="字幕字型檔路徑；預設自動找思源黑體")
    ap.add_argument("--font-family", help="ASS 用的字型家族名，例如 'Noto Sans CJK TC'。"
                                         "指定 .ttc 這種多家族字型檔時需要")
    ap.add_argument("--edl", default=str(ROOT / "edl.json"))
    args = ap.parse_args()

    edl_path = pathlib.Path(args.edl)
    if not edl_path.exists():
        print(f"找不到 {edl_path}", file=sys.stderr)
        return 1
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    if not edl.get("segments"):
        print("edl.json 還沒有 segments — 需要先盤點素材決定剪點", file=sys.stderr)
        return 1

    missing = [s["src"] for s in edl["segments"] if not (RAW / s["src"]).exists()]
    if missing:
        print(f"raw/ 缺少這些素材：{', '.join(sorted(set(missing)))}", file=sys.stderr)
        return 1

    font_path, font_family = pick_font(args.font, args.font_family)
    print(f"字幕字型：{font_family}（{font_path}）")
    if "WenQuanYi" in font_family:
        print("提醒：WQY Zen Hei 是最後備援，字重不足；裝 fonts-noto-cjk 或用 --font 指定品牌字型")

    for aspect in args.aspect or ["9:16", "4:5"]:
        render(edl, aspect, args.draft, font_path, font_family)
    print(f"\n完成，檔案在 {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
