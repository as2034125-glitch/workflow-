#!/usr/bin/env python3
"""從 Google Drive 下載素材到 raw/。

需要資料夾設為「知道連結的人可檢視」，且執行環境的網路政策允許
drive.google.com。目前 session 的 proxy 對該網域回 403，所以這支腳本
要等網路開通後才跑得動。

用法：
    python3 scripts/fetch.py            # 下載 manifest.json 列出的全部檔案
    python3 scripts/fetch.py --only mp4 # 只抓影片
"""

import argparse
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
MANIFEST = ROOT / "manifest.json"
BASE = "https://drive.google.com/uc?export=download"


def download(file_id: str, dest: pathlib.Path) -> None:
    """抓單一檔案。Drive 對大檔會先回一頁病毒掃描確認頁，要撈出 token 再送一次。"""
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    url = f"{BASE}&id={file_id}"

    with opener.open(url, timeout=120) as resp:
        head = resp.read(8192)
        if head[:4] == b"\x00\x00\x00\x20" or not head.lstrip().startswith(b"<"):
            # 已經是二進位內容，直接把剩下的寫完
            with dest.open("wb") as fh:
                fh.write(head)
                while chunk := resp.read(1 << 20):
                    fh.write(chunk)
            return
        body = head + resp.read()

    token = re.search(rb'name="confirm"\s+value="([^"]+)"', body)
    if not token:
        raise RuntimeError(f"{file_id}: 拿不到確認 token，資料夾可能未開放連結存取")

    confirmed = f"{url}&confirm={urllib.parse.quote(token.group(1).decode())}"
    with opener.open(confirmed, timeout=600) as resp, dest.open("wb") as fh:
        while chunk := resp.read(1 << 20):
            fh.write(chunk)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="只抓這個副檔名，例如 mp4")
    args = ap.parse_args()

    if not MANIFEST.exists():
        print(f"找不到 {MANIFEST}", file=sys.stderr)
        return 1

    RAW.mkdir(exist_ok=True)
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    if args.only:
        entries = [e for e in entries if e["title"].endswith(args.only)]

    failed = []
    for i, entry in enumerate(entries, 1):
        dest = RAW / entry["title"]
        if dest.exists() and dest.stat().st_size == int(entry["size"]):
            print(f"[{i}/{len(entries)}] 已存在，跳過 {entry['title']}")
            continue
        print(f"[{i}/{len(entries)}] 下載 {entry['title']} ({int(entry['size'])/1e6:.1f} MB)")
        try:
            download(entry["id"], dest)
        except Exception as exc:  # noqa: BLE001 — 逐檔回報，不讓單一失敗中斷整批
            print(f"    失敗：{exc}", file=sys.stderr)
            dest.unlink(missing_ok=True)
            failed.append(entry["title"])

    if failed:
        print(f"\n{len(failed)} 個檔案失敗：{', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"\n完成，{len(entries)} 個檔案在 {RAW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
