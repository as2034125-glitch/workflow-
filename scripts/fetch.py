#!/usr/bin/env python3
"""從 Google Drive 下載素材到 raw/。

有兩條路，會自動選：

1. **Drive API（建議）** — 走 `www.googleapis.com`，這個網域在目前的執行環境
   已經放行，不用改網路政策。需要一把 Google API 金鑰（只要 API key，不用
   OAuth，因為素材資料夾已設為「知道連結的人可檢視」）：

       export GOOGLE_API_KEY=...
       python3 scripts/fetch.py

2. **公開連結** — 走 `drive.google.com`。目前 session 的 proxy 對該網域回
   403，要先把 `drive.google.com` 與 `drive.usercontent.google.com` 加進
   環境的網路白名單才跑得動。沒給金鑰時會走這條。

用法：
    python3 scripts/fetch.py                 # 下載 manifest.json 列出的全部檔案
    python3 scripts/fetch.py --only mp4      # 只抓影片
    python3 scripts/fetch.py --api-key AIza… # 直接指定金鑰，不用環境變數
"""

import argparse
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
MANIFEST = ROOT / "manifest.json"
PUBLIC_BASE = "https://drive.google.com/uc?export=download"
API_BASE = "https://www.googleapis.com/drive/v3/files"
ATTEMPTS = 3


class PermanentError(RuntimeError):
    """重試也不會好的錯誤，例如金鑰無效或檔案沒有開放存取。"""


def _stream_to(resp, dest: pathlib.Path, head: bytes = b"") -> None:
    with dest.open("wb") as fh:
        if head:
            fh.write(head)
        while chunk := resp.read(1 << 20):
            fh.write(chunk)


def download_api(file_id: str, dest: pathlib.Path, api_key: str) -> None:
    """走 Drive API 直接取檔內容。公開檔案用 API key 就夠，不需要 OAuth。"""
    query = urllib.parse.urlencode({"alt": "media", "key": api_key})
    url = f"{API_BASE}/{file_id}?{query}"
    try:
        with urllib.request.urlopen(url, timeout=600) as resp:
            _stream_to(resp, dest)
    except urllib.error.HTTPError as exc:
        body = exc.read(4096).decode("utf-8", "replace").strip()
        try:
            detail = json.loads(body)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            detail = body[:200]
        msg = f"Drive API 回 {exc.code} — {detail}"
        # 4xx 多半是金鑰或權限問題，重試沒有意義；429 是流量限制，值得等一下再試
        if 400 <= exc.code < 500 and exc.code != 429:
            raise PermanentError(msg) from exc
        raise RuntimeError(msg) from exc


def download_public(file_id: str, dest: pathlib.Path) -> None:
    """抓公開連結。Drive 對大檔會先回一頁病毒掃描確認頁，要撈出 token 再送一次。"""
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    url = f"{PUBLIC_BASE}&id={file_id}"

    with opener.open(url, timeout=120) as resp:
        head = resp.read(8192)
        if head[:4] == b"\x00\x00\x00\x20" or not head.lstrip().startswith(b"<"):
            # 已經是二進位內容，直接把剩下的寫完
            _stream_to(resp, dest, head)
            return
        body = head + resp.read()

    token = re.search(rb'name="confirm"\s+value="([^"]+)"', body)
    if not token:
        raise RuntimeError(f"{file_id}: 拿不到確認 token，資料夾可能未開放連結存取")

    confirmed = f"{url}&confirm={urllib.parse.quote(token.group(1).decode())}"
    with opener.open(confirmed, timeout=600) as resp:
        _stream_to(resp, dest)


def fetch_one(entry: dict, dest: pathlib.Path, api_key: str | None) -> None:
    """下載單一檔案並核對大小，失敗會重試幾次（網路抖動居多）。"""
    expected = int(entry["size"])
    last: Exception | None = None

    for attempt in range(1, ATTEMPTS + 1):
        try:
            if api_key:
                download_api(entry["id"], dest, api_key)
            else:
                download_public(entry["id"], dest)

            actual = dest.stat().st_size
            if actual != expected:
                raise RuntimeError(f"大小不符：預期 {expected}，實得 {actual}")
            return
        except PermanentError:
            dest.unlink(missing_ok=True)
            raise
        except Exception as exc:  # noqa: BLE001 — 逐次重試，最後一次才往上拋
            last = exc
            dest.unlink(missing_ok=True)
            if attempt < ATTEMPTS:
                wait = 2 ** attempt
                print(f"    第 {attempt} 次失敗（{exc}），{wait}s 後重試")
                time.sleep(wait)

    raise last  # type: ignore[misc]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="只抓這個副檔名，例如 mp4")
    ap.add_argument("--api-key", help="Google API 金鑰；預設讀 GOOGLE_API_KEY")
    args = ap.parse_args()

    api_key = args.api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GDRIVE_API_KEY")

    if not MANIFEST.exists():
        print(f"找不到 {MANIFEST}", file=sys.stderr)
        return 1

    RAW.mkdir(exist_ok=True)
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    if args.only:
        entries = [e for e in entries if e["title"].endswith(args.only)]

    if api_key:
        print("走 Drive API（www.googleapis.com）")
    else:
        print("沒有 API 金鑰，改走 drive.google.com 公開連結；"
              "若環境未放行該網域會全部失敗", file=sys.stderr)

    failed = []
    for i, entry in enumerate(entries, 1):
        dest = RAW / entry["title"]
        if dest.exists() and dest.stat().st_size == int(entry["size"]):
            print(f"[{i}/{len(entries)}] 已存在，跳過 {entry['title']}")
            continue
        print(f"[{i}/{len(entries)}] 下載 {entry['title']} ({int(entry['size'])/1e6:.1f} MB)")
        try:
            fetch_one(entry, dest, api_key)
        except Exception as exc:  # noqa: BLE001 — 逐檔回報，不讓單一失敗中斷整批
            print(f"    失敗：{exc}", file=sys.stderr)
            failed.append(entry["title"])

    if failed:
        print(f"\n{len(failed)} 個檔案失敗：{', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"\n完成，{len(entries)} 個檔案在 {RAW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
