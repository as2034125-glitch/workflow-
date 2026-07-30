#!/usr/bin/env python3
"""盤點 raw/ 的素材，並抽出縮圖供分鏡判讀。

產出：
    inventory.json          每支片的長度／解析度／fps／音軌／位元率
    docs/03-素材清單.md      人看的表格
    frames/<檔名>/NNN.jpg    每支片平均抽 6 張，用來決定哪顆鏡頭進片

用法：
    python3 scripts/probe.py
"""

import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _ffmpeg import FFMPEG, FFPROBE  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
FRAMES = ROOT / "frames"
FRAMES_PER_CLIP = 6


def probe(path: pathlib.Path) -> dict:
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(out.stdout)
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)

    fps = 0.0
    if video and "/" in video.get("r_frame_rate", ""):
        num, den = video["r_frame_rate"].split("/")
        fps = round(int(num) / int(den), 2) if int(den) else 0.0

    # 手機直拍的檔案常是橫向存檔＋旋轉中繼資料，ffmpeg 解碼時會自動轉正。
    # 這裡要報「轉正後」的尺寸，否則直式素材會被誤判成橫式。
    width = video["width"] if video else 0
    height = video["height"] if video else 0
    rotation = 0
    for side in (video or {}).get("side_data_list", []):
        if "rotation" in side:
            rotation = int(side["rotation"])
    if rotation % 180 != 0:
        width, height = height, width

    return {
        "file": path.name,
        "duration": round(float(data["format"]["duration"]), 2),
        "size_mb": round(int(data["format"]["size"]) / 1e6, 2),
        "bitrate_kbps": round(int(data["format"].get("bit_rate", 0)) / 1000),
        "width": width,
        "height": height,
        "rotation": rotation,
        "fps": fps,
        "has_audio": audio is not None,
        "audio_codec": audio["codec_name"] if audio else None,
    }


def extract_frames(path: pathlib.Path, duration: float) -> None:
    out_dir = FRAMES / path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    # 頭尾各留 5%，避免抽到轉場黑幀
    span = duration * 0.9
    for i in range(FRAMES_PER_CLIP):
        ts = duration * 0.05 + span * i / max(FRAMES_PER_CLIP - 1, 1)
        subprocess.run(
            [FFMPEG, "-nostdin", "-v", "error", "-y", "-ss", f"{ts:.2f}",
             "-i", str(path), "-frames:v", "1", "-vf", "scale=480:-2",
             str(out_dir / f"{i:03d}.jpg")],
            check=True,
        )


def main() -> int:
    if FFPROBE is None:
        print("找不到 ffprobe，請先安裝 ffmpeg 套件（apt-get install ffmpeg）", file=sys.stderr)
        return 1
    if not RAW.exists() or not any(RAW.iterdir()):
        print(f"{RAW} 是空的，請先跑 scripts/fetch.py", file=sys.stderr)
        return 1

    clips = sorted(p for p in RAW.iterdir() if p.suffix.lower() in {".mp4", ".mov"})
    inventory = []
    for i, path in enumerate(clips, 1):
        print(f"[{i}/{len(clips)}] {path.name}")
        info = probe(path)
        extract_frames(path, info["duration"])
        inventory.append(info)

    (ROOT / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(c["duration"] for c in inventory)
    lines = [
        "# 素材清單",
        "",
        f"共 {len(inventory)} 支，總長 {total:.1f} 秒（{total/60:.1f} 分）。",
        "",
        "| 檔案 | 長度 | 解析度 | fps | 位元率 | 音軌 |",
        "|---|---|---|---|---|---|",
    ]
    for c in inventory:
        audio = c["audio_codec"] or "無"
        lines.append(
            f"| {c['file']} | {c['duration']}s | {c['width']}×{c['height']} "
            f"| {c['fps']} | {c['bitrate_kbps']} kbps | {audio} |"
        )
    (ROOT / "docs" / "03-素材清單.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n盤點完成：{len(inventory)} 支、總長 {total:.1f} 秒")
    print(f"縮圖在 {FRAMES}，逐張看過後把選定的鏡頭填進 edl.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
