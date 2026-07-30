# 植感醇黑可可 — 沖泡系列剪輯

IG Reels + Facebook 廣告用的 30 秒影片，從 Google Drive 素材到多比例成品的完整流程。

## 現況

| 項目 | 狀態 |
|---|---|
| 規格確認 | 完成 — `docs/01-剪輯規格.md` |
| 旁白稿與字幕文案 | 完成 — `docs/02-腳本-30秒.md` |
| 廣告用字檢查 | 完成 — `docs/04-廣告用字檢查.md` |
| 剪輯 pipeline | 完成，已用合成素材驗證通過 |
| 素材下載 | **受阻** — 見下方 |
| 分鏡與剪點 | 待素材到位 |

### 待解：素材下載被網路政策擋住

Drive 資料夾 `醇黑可可_沖泡系列_raw`（ID `1m7nALsFI9SkLRmDwbcZSHTuitoDQaRR8`）內有 22 支影片、10 張照片，清單已存在 `manifest.json`。但執行環境的 proxy 對 `drive.google.com` 回 403：

```
connect_rejected: gateway answered 403 to CONNECT
host: drive.google.com:443
```

**解法**：把環境的網路政策改成允許下列網域，並將該 Drive 資料夾設為「知道連結的人可檢視」，然後開新 session。設定說明見 https://code.claude.com/docs/en/claude-code-on-the-web

```
drive.google.com
drive.usercontent.google.com
*.googleusercontent.com
```

第二個網域容易漏掉 —— Drive 的實際檔案內容是從 `drive.usercontent.google.com` 送出的，只開 `drive.google.com` 會卡在重導向那一步。

### 新 session 的第一步

```bash
git fetch origin && git checkout claude/cacao-video-editing-4sjzs5
apt-get update -qq && apt-get install -y -qq ffmpeg   # 容器預設沒有 ffprobe
python3 scripts/fetch.py && python3 scripts/probe.py
```

跑完後 `frames/` 會有每支片的 6 張縮圖，逐張看過決定哪顆鏡頭進片，填進 `edl.json` 的 `segments`，再跑 `scripts/build.py --draft`。腳本與規格都已定案，見 `docs/`。

## 流程

```bash
python3 scripts/fetch.py     # 依 manifest.json 下載素材到 raw/
python3 scripts/probe.py     # 盤點規格 + 每支抽 6 張縮圖到 frames/
                             # → 看過縮圖後，把選定的鏡頭與時間碼填進 edl.json
python3 scripts/build.py --draft   # 低畫質預覽，確認節奏
python3 scripts/build.py           # 正式輸出 9:16 與 4:5
```

`edl.json` 是唯一的剪輯決策來源。改剪點、改字幕、換配樂都只動它，不要改 `scripts/build.py`。

## 已驗證

用 7 顆合成素材跑完整條 pipeline，產出：

- `cacao_30s_9x16.mp4` — 30.00 秒，1080×1920，yuv420p，AAC 立體聲
- `cacao_30s_4x5.mp4` — 30.00 秒，1080×1350，同上

確認項目：橫式素材正確裁成直式、繁體中文字幕正常渲染、`**24g**` 重音標記放大並套上重音色、片尾警語落在安全區內、旁白進來時配樂自動壓低（sidechain ducking）。

## 開工前還需要的東西

1. **旁白錄音**（單軌乾聲，稿在 `docs/02-腳本-30秒.md`），放專案根目錄後填進 `edl.json` 的 `audio.voiceover`
2. **有授權的配樂**，同樣填 `audio.bgm`
3. **品牌字型檔** — 目前用系統備援的 WQY Zen Hei，字重不足，做廣告會拉低質感。用 `--font` 指定
4. **品牌主色** — `scripts/build.py` 的 `ACCENT` 目前是暫定的可可金 `#E8B24A`
5. **原始畫質素材**（如果拿得到）— 現有檔名為 LINE 導出格式，已被二次壓縮，22 支平均不到 5 MB

## 兩件會影響投放的事

- 廣告導購請指向 **12 入**。1 入規格（SKU `VG00C1`）目前庫存為 0。
- 片尾 Q10 警語為法定標示，已寫進 `edl.json` 的 `disclaimer`，不要拿掉。
