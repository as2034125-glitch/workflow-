# 植感醇黑可可 — 沖泡系列剪輯

IG Reels + Facebook 廣告用的 30 秒影片，從 Google Drive 素材到多比例成品的完整流程。

## 現況

| 項目 | 狀態 |
|---|---|
| 規格確認 | 完成 — `docs/01-剪輯規格.md` |
| 旁白稿與字幕文案 | 完成 — `docs/02-腳本-30秒.md` |
| 廣告用字檢查 | 完成 — `docs/04-廣告用字檢查.md` |
| 剪輯 pipeline | 完成，已用合成素材驗證通過 |
| 素材清單核對 | 完成 — `manifest.json` 與 Drive 現況完全相符（2026-07-30 查） |
| 素材下載 | 完成 — 33 個檔案，走 Drive API |
| 素材盤點 | 完成 — `docs/03-素材清單.md`，22 支全為 720×1280 直式 |
| 分鏡與剪點 | 初剪完成 — `edl.json` 8 段接滿 30.00 秒 |
| 成品 | 待旁白、配樂、品牌字型到位後正式輸出 |

### 素材本身的四個限制（會影響成效，先講清楚）

1. **沒有情境鏡頭。** 22 支全是辦公桌面的產品示範，沒有任何「下午三點想喝手搖」的生活情境。腳本第 1 句與第 6 句（`下午茶 換這杯`）目前只能用成品杯頂著，說服力打折。
2. **沒有沖水畫面。** 字幕寫「熱水一沖」，但素材裡沒有任何倒水鏡頭，只有倒粉。目前該段配的是倒粉畫面，畫面與文案對不上。
3. **背景雜。** 白桌上有筆電、螢幕（風景桌布）、白色電線，多數鏡頭都入鏡，廣告質感偏弱。
4. **解析度只有 720×1280。** 輸出 1080×1920 要放大 1.5 倍，銳利度不足；檔名是 LINE 導出格式，已經過二次壓縮。

補拍的話，優先序是 情境鏡頭 > 沖水特寫 > 乾淨背景重拍產品。

### Drive 下載方式

Drive 資料夾 `醇黑可可_沖泡系列_raw`（ID `1m7nALsFI9SkLRmDwbcZSHTuitoDQaRR8`）內有 22 支影片、11 張照片，共 109.1 MB。已逐筆核對過，`manifest.json` 的 33 筆檔名、ID、大小與 Drive 現況完全一致，不需重建清單。

資料夾的共用設定也已經是對外開放（`anyone`），所以**不用再改共用權限**。

> ⚠️ 順帶一提：該資料夾目前對 `anyone` 開的是 **編輯者（writer）**，等於拿到連結的人都能改或刪掉原始素材。下載只需要「檢視者」，建議降權成 reader。

卡住的只有執行環境的網路政策 —— proxy 對 `drive.google.com` 回 403：

```
connect_rejected: gateway answered 403 to CONNECT
host: drive.google.com:443
```

當初卡在網路政策，解法如下（**建議走 A**，已實測可用）：

#### A. 給一把 Google API 金鑰（不用改環境，最快）

實測 `www.googleapis.com` 在目前環境**已經放行**，所以走 Drive API 就繞開了被擋的網域。素材是公開的，只要一把 API key，不需要 OAuth：

1. 到 Google Cloud Console 建一個專案 → 啟用 **Google Drive API** → 建立憑證選 **API 金鑰**
2. 把金鑰交給 session（或設進環境變數），然後：

```bash
export GOOGLE_API_KEY=AIza...
python3 scripts/fetch.py
```

`scripts/fetch.py` 已經支援這條路，有金鑰就自動走 API，沒有才回頭走公開連結。

#### B. 改環境的網路白名單

把下列網域加進環境的網路政策，然後開新 session。設定說明見 https://code.claude.com/docs/en/claude-code-on-the-web

```
drive.google.com
drive.usercontent.google.com
*.googleusercontent.com
```

第二個網域容易漏掉 —— Drive 的實際檔案內容是從 `drive.usercontent.google.com` 送出的，只開 `drive.google.com` 會卡在重導向那一步。（三個目前都是擋的，已實測。）

### 新 session 的第一步

```bash
git fetch origin && git checkout claude/cacao-video-editing-no5aac
apt-get update -qq && apt-get install -y -qq ffmpeg   # 容器預設沒有 ffprobe
export GOOGLE_API_KEY=AIza...                         # 素材不進版控，要重抓
python3 scripts/fetch.py
python3 scripts/build.py --draft                      # edl.json 剪點已填好
```

`raw/`、`out/`、`frames/` 都不進版控，新容器要重跑 `fetch.py`。剪點已經在 `edl.json` 裡，直接 build 就有初剪。要調整剪點只動 `edl.json`。

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

用 7 顆合成素材（混 1920×1080、1280×720、1080×1080、1080×1920）跑完整條 pipeline，2026-07-30 在乾淨容器上重跑確認仍可通過，產出：

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
