/**
 * 從 recipes.json 產生內部提案書（.docx）。
 *
 * 附錄 A 的 100 種配方、附錄 B 的警語適用編號，全部由 recipes.json 生成，
 * 不會跟 01-100種喝法清單.md 脫鉤。改配方的流程是：
 *
 *     改 docs/100-ways/01-100種喝法清單.md
 *     python3 scripts/recipes.py      # 重新產生 recipes.json
 *     node scripts/proposal.js        # 重新產生提案書
 *
 * 需要 docx 套件（容器預設沒有）：
 *     npm install docx
 */

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  PageBreak, TableOfContents, Footer, PageNumber, LevelFormat, convertInchesToTwip,
} = require("docx");

const REPO = path.resolve(__dirname, "..");
const recipesDoc = JSON.parse(
  fs.readFileSync(path.join(REPO, "docs/100-ways/recipes.json"), "utf-8")
);

const FONT = "微軟正黑體";
const W = 9026;               // A4 內容寬度 (11906 - 2*1440)
const INK = "2B2724";
const MUTED = "6B6560";
const GOLD = "E8B24A";
const HEAD_BG = "3A3634";
const ZEBRA = "F6F3EE";
const LINE = "D8D2C8";

/* ---------- helpers ---------- */

const p = (text, o = {}) =>
  new Paragraph({
    alignment: o.align,
    spacing: { before: o.before ?? 0, after: o.after ?? 120, line: o.line ?? 300 },
    indent: o.indent,
    numbering: o.numbering,
    border: o.border,
    children: [].concat(text).map((t) =>
      typeof t === "string"
        ? new TextRun({ text: t, size: o.size ?? 21, color: o.color ?? INK, bold: o.bold, italics: o.italics })
        : t
    ),
  });

const run = (text, o = {}) =>
  new TextRun({ text, size: o.size ?? 21, color: o.color ?? INK, bold: o.bold, italics: o.italics });

const h1 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 400, after: 200 },
    children: [new TextRun({ text, size: 30, bold: true, color: INK })],
  });

const h2 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 300, after: 140 },
    children: [new TextRun({ text, size: 24, bold: true, color: INK })],
  });

const bullet = (text, o = {}) =>
  p(text, { ...o, numbering: { reference: "dot", level: 0 }, after: 80 });

const spacer = (h = 200) => new Paragraph({ spacing: { after: h }, children: [] });

const noBorders = {
  top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
  left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
};

function cell(content, width, o = {}) {
  const kids = [].concat(content).map((c) =>
    typeof c === "string"
      ? new Paragraph({
          alignment: o.align,
          spacing: { before: 40, after: 40, line: 260 },
          children: [new TextRun({ text: c, size: o.size ?? 18, bold: o.bold, color: o.color ?? INK })],
        })
      : c
  );
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    columnSpan: o.span,
    shading: o.fill ? { type: ShadingType.CLEAR, fill: o.fill, color: "auto" } : undefined,
    margins: { top: 90, bottom: 90, left: 120, right: 120 },
    verticalAlign: o.valign,
    children: kids.length ? kids : [new Paragraph({ children: [] })],
  });
}

/**
 * rows: 第一列為表頭。cols: 各欄寬度 (DXA)，總和須等於 W。
 */
function table(cols, rows, o = {}) {
  const total = cols.reduce((a, b) => a + b, 0);
  if (total !== W) throw new Error(`欄寬總和 ${total} ≠ ${W}`);

  const trs = rows.map((cells, ri) => {
    const isHead = ri === 0 && !o.noHead;
    return new TableRow({
      tableHeader: isHead,
      children: cells.map((c, ci) => {
        const spec = typeof c === "object" && c !== null && !Array.isArray(c) ? c : { text: c };
        const span = spec.span ?? 1;
        const width = cols.slice(ci, ci + span).reduce((a, b) => a + b, 0);
        return cell(spec.text, width, {
          span: span > 1 ? span : undefined,
          bold: isHead || spec.bold,
          color: isHead ? "FFFFFF" : spec.color,
          fill: isHead ? HEAD_BG : spec.fill ?? (o.zebra && ri % 2 === 0 ? ZEBRA : undefined),
          align: spec.align ?? o.align?.[ci],
          size: o.size,
          valign: "center",
        });
      }),
    });
  });

  return new Table({
    columnWidths: cols,
    width: { size: W, type: WidthType.DXA },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: LINE },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: LINE },
      left: { style: BorderStyle.SINGLE, size: 4, color: LINE },
      right: { style: BorderStyle.SINGLE, size: 4, color: LINE },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: LINE },
      insideVertical: { style: BorderStyle.SINGLE, size: 2, color: LINE },
    },
    rows: trs,
  });
}

const rule = () =>
  new Paragraph({
    spacing: { before: 60, after: 240 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: GOLD } },
    children: [],
  });

const note = (text) =>
  p(text, { size: 17, color: MUTED, after: 200, line: 260 });

/* ---------- 封面 ---------- */

const cover = [
  spacer(2600),
  p("內部提案書", { size: 20, color: GOLD, bold: true, align: AlignmentType.CENTER, after: 160 }),
  p("蛋白飲的 100 種喝法", { size: 52, bold: true, align: AlignmentType.CENTER, after: 120 }),
  p("20 週社群內容企劃", { size: 26, color: MUTED, align: AlignmentType.CENTER, after: 400 }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 400 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: GOLD } },
    children: [],
  }),
  p("把豌豆蛋白飲從健身補給品，改寫成手搖飲的日常替代選項", {
    size: 22, color: MUTED, align: AlignmentType.CENTER, after: 1400,
  }),
  new Table({
    columnWidths: [2400, 3600],
    width: { size: 6000, type: WidthType.DXA },
    alignment: AlignmentType.CENTER,
    borders: {
      ...noBorders,
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: LINE },
      insideVertical: { style: BorderStyle.NONE },
    },
    rows: [
      ["提案品牌", "AGUGU"],
      ["提案日期", "2026 年 8 月 1 日"],
      ["企劃期間", "20 週（建議 9 月第一週開跑）"],
      ["文件版本", "v1.0"],
    ].map(([k, v]) =>
      new TableRow({
        children: [
          cell(k, 2400, { size: 19, color: MUTED }),
          cell(v, 3600, { size: 19, bold: true }),
        ],
      })
    ),
  }),
  new Paragraph({ children: [new PageBreak()] }),
];

/* ---------- 目錄 ---------- */

const toc = [
  h1("目錄"),
  new TableOfContents("目錄", { hyperlink: true, headingStyleRange: "1-2" }),
  note("（在 Word 中按 Ctrl+A 後按 F9 可更新頁碼）"),
  new Paragraph({ children: [new PageBreak()] }),
];

/* ---------- 1 提案摘要 ---------- */

const s1 = [
  h1("1　提案摘要"),
  rule(),
  p([
    run("AGUGU 現有 8 個隨手包口味，一杯 55 元，價格帶正好落在手搖飲的中杯區間。本案提議用 "),
    run("100 支短影片", { bold: true }),
    run("，在 20 週內把「豌豆蛋白飲」的認知從健身補給品，改寫成手搖飲的日常替代選項。"),
  ]),
  spacer(120),
  table([2000, 7026], [
    ["項目", "內容"],
    ["核心主張", "手搖飲想喝的那個位置，換這杯"],
    ["產出規模", "100 支短影片（15–18 秒，9:16）＋ 20 支週合集（30 秒，4:5）"],
    ["執行方式", "品牌自製 70 支，後段開放 UGC 徵集補完 30 支"],
    ["期間", "前製 4 週 ＋ 發布 20 週"],
    ["主標籤", "#AGUGU100種喝法　／　投稿標籤 #我的第101種喝法"],
    ["投放平台", "IG Reels（單支 9:16）、Facebook（週合集 4:5）"],
    ["預估物料成本", "約 NT$50,600（不含人力、場地、器材與廣告投放）"],
    [{ text: "最大風險", bold: true }, { text: "多個主打口味目前缺貨，不補貨會讓近半內容導向買不到的商品", bold: true }],
  ], { zebra: true }),
  spacer(200),
  h2("為什麼是 100 種，而不是一支好廣告"),
  p("既有的 30 秒可可廣告已經驗證過「下午三點，又想點手搖了」這個切角。但單支廣告只能講一種喝法，而本案要解的是三個單支廣告解不掉的問題："),
  spacer(80),
  table([2800, 6226], [
    ["現況問題", "100 種喝法怎麼解"],
    ["消費者買了一盒 12 包，喝到第 4 包就膩，不回購", "每支影片就是一個「今天喝什麼」的答案"],
    ["8 個口味的差異講不清楚，新客不知道從哪個入手", "用喝法反推口味：想喝奶茶 → 奶霧紅茶"],
    ["蛋白飲被歸類成「健身的人才喝的東西」", "內容全部發生在辦公室、超商、廚房，不是健身房"],
  ], { zebra: true }),
];

/* ---------- 2 企劃內容 ---------- */

const seriesTable = recipesDoc.series.map((s) => {
  const cta = {
    S1: "新客首購組", S2: "不導購（養流量）", S3: "3 盒組", S4: "拿鐵／奶霧紅茶",
    S5: "不導購（養流量）", S6: "新客首購組", S7: "綜合穀物／500g 袋裝",
    S8: "3–4 盒組", S9: "500g 袋裝", S10: "零咖啡因組",
  }[s.id];
  return [s.id, s.title, `#${String(s.from).padStart(3, "0")}–#${String(s.to).padStart(3, "0")}`, cta];
});

const s2 = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("2　企劃內容"),
  rule(),
  h2("2.1　執行主體與節奏"),
  p("品牌自製 70 支，後段開放 UGC 補完 30 支，共 20 週。"),
  spacer(80),
  table([1800, 7226], [
    ["期間", "工作內容"],
    ["W-4 ～ W-1", "前製：批次拍攝 70 支（6 個拍攝日）"],
    ["W1 ～ W14", "品牌發布 #001–#070，每週一至週五各 1 支"],
    ["W12 ～ W16", "UGC 徵集期（與發布期重疊，趁聲量最高時開跑）"],
    ["W15 ～ W20", "發布 #071–#100，全部來自消費者投稿"],
  ], { zebra: true }),
  spacer(160),
  p([
    run("每週五加發一支「本週合集」（該週 5 支各取 5–6 秒剪成 30 秒），共 20 支。這是"),
    run("二次利用，不是新拍", { bold: true }),
    run("，剪輯成本極低但補足了「一次看多種」的需求。"),
  ]),

  h2("2.2　UGC 機制：編號本身就是獎品"),
  p("徵集期的訴求不是「投稿抽獎」，而是「你的喝法會變成 #087」。100 個編號留 30 個空著，投稿被選中的人，作品掛上永久編號並由官方帳號發布、標註創作者。這比抽獎更能驅動有創意的投稿，成本也低。"),
  spacer(80),
  bullet("主標籤 #AGUGU100種喝法"),
  bullet("投稿標籤 #我的第101種喝法（徵集期後仍可持續使用，讓企劃有長尾）"),
  bullet("選中者獎勵：該口味 1 盒 ＋ 搖搖杯 ＋ 官方帳號發布並標註"),
  spacer(120),
  p([
    run("冷啟動風險：", { bold: true }),
    run("UGC 徵集不能提早到聲量建立之前。前 70 支必須先跑完大半，讓「編號」這件事被認得，投稿才會來。若 W12 時主標籤的自然使用量低於 50 則，建議把徵集延後 2 週，並改用邀請制（先私訊 20 位既有回購客）暖場。"),
  ]),

  h2("2.3　內容架構：10 系列 × 10 種"),
  p("系列化不是為了整齊，是為了讓觀眾在第 30 支的時候還知道自己在看什麼。完整 100 種配方見附錄 A。"),
  spacer(80),
  table([900, 2800, 1900, 3426], [
    ["系列", "主題", "編號", "主要導購"],
    ...seriesTable,
  ], { zebra: true, align: [AlignmentType.CENTER, undefined, AlignmentType.CENTER, undefined] }),
  spacer(160),
  p("S1 排第一是刻意的——它直接對標珍奶、鮮奶茶、抹茶拿鐵，是整個企劃的論點。後面 9 個系列都是這個論點的展開。"),
];

/* ---------- 3 目標與 CTA ---------- */

const s3 = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("3　目標與 CTA 配置"),
  rule(),
  p("本案同時要拉新客、拉客單與回購、拉聲量。這三件事的 CTA 不一樣，因此按系列輪替，不要每支都喊同一個連結。"),
  spacer(80),
  table([1800, 1500, 2400, 3326], [
    ["目標", "對應系列", "CTA 訴求", "導購商品"],
    ["拉新客首購", "S1、S6", "第一次喝，從這杯開始", "新手入門組 NT$899（12 入＋搖搖杯）／入門全配組 NT$799"],
    ["提高客單與回購", "S3、S7、S8、S9", "一天喝好幾種／常備", "3 盒組 NT$1,760–1,782、4 盒組 NT$2,299、500g 袋裝 NT$439"],
    ["聲量與品牌記憶", "S2、S5", "不放購買連結，只放標籤", "—"],
    ["情境定位", "S4、S10", "單一口味頁", "拿鐵／零咖啡因組 NT$1,760"],
  ], { zebra: true }),
  spacer(200),
  p([
    run("S2 與 S5 完全不導購是刻意的。", { bold: true }),
    run("100 支影片支支導購會被演算法判定為純商業內容，觸及會掉；留兩個系列做純內容，養自然流量。"),
  ]),

  h1("4　成效衡量"),
  rule(),
  p("前 4 週為基準期，不設達標門檻，只收數據。第 5 週起以前 4 週的中位數為基準。"),
  spacer(80),
  table([2600, 6426], [
    ["指標", "怎麼看"],
    ["單支平均觀看完成率", "15 秒影片，目標 > 60%。低於 40% 表示前 2 秒的鉤子失敗，不是內容問題"],
    ["系列間表現差異", "每 10 支一個系列，比較系列平均。表現最差的系列在 UGC 階段不要重複"],
    ["主標籤自然使用則數", "UGC 徵集是否如期開跑的判斷依據（門檻 50 則）"],
    ["導購 vs 非導購系列的觸及差", "驗證「留兩個系列養流量」這個假設是否成立"],
    ["新客首購轉換", "只看 S1、S6 檔期的新客數"],
    ["回購率與客單價", "看 3 盒以上組合的訂單佔比變化"],
  ], { zebra: true }),
  spacer(200),
  p([
    run("不要用單支爆紅當成功指標。", { bold: true }),
    run("本案的價值在於 100 支的累積與「收集感」，單支數據會被演算法隨機性主導。"),
  ]),
];

/* ---------- 5 執行計畫 ---------- */

const s5 = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("5　執行計畫"),
  rule(),
  h2("5.1　核心原則：模板化，不是創作化"),
  p("100 支影片不是拍 100 次，是拍 6 次。單支的質感由模板保證，不由個別發揮保證。100 支如果每支都重新想分鏡、重新打燈、重新錄旁白，一定拍不完——這是這類企劃最常見的死法。"),
  spacer(80),
  table([1400, 3400, 4226], [
    ["項目", "決定", "為什麼"],
    ["機位", "俯拍＋45 度側拍，兩機固定不動", "不用重打燈，換配方只換桌上的東西"],
    ["聲音", "不錄旁白，只用現場環境音＋字卡", "省掉 100 次配音、對稿、混音；環境音本身就是這類內容的賣點"],
    ["道具", "全系列統一同一個搖搖杯", "100 支同一個杯子＝品牌識別"],
  ], { zebra: true }),
  spacer(160),
  p("搖搖杯建議用經典黑色搖搖杯（提環），SKU P0016S，庫存 150 足夠。白色與紫色目前掛 0，不要選。"),

  h2("5.2　影片模板（15–18 秒，9:16）"),
  table([1600, 5000, 2426], [
    ["時間", "內容", "機位"],
    ["0.0–2.0", "成品先出——完成的那杯，喝一口", "45 度"],
    ["2.0–4.0", "編號卡進場：#037 / 100 ＋ 喝法名稱", "俯拍"],
    ["4.0–11.0", "製作過程：撕包 → 倒入 → 加液體 → 搖", "俯拍為主，中間切一顆 45 度"],
    ["11.0–14.0", "倒出／成品特寫（該支的影片鉤子在這裡）", "45 度"],
    ["14.0–17.0", "CTA 字卡 ＋ 法定警語小字", "定格"],
  ], { zebra: true }),
  spacer(160),
  p([
    run("前 2 秒放成品不放過程", { bold: true }),
    run("，這是完成率的關鍵。觀眾要先看到「這杯長什麼樣」才願意留下來看怎麼做。"),
  ]),
  p("畫面右上角固定顯示 #037 / 100，全系列同一位置、同一字級。這是整個企劃「收集感」的視覺載體，也是 UGC 階段那個鉤子的基礎，位置不要換。"),
  note("字卡與警語的安全區沿用既有剪輯規格：上緣 220px、下緣 420px、左右各 60px，字幕基線壓在 y ≈ 1250–1400，警語小字常駐至少 3 秒。"),

  h2("5.3　批次拍攝：6 個拍攝日"),
  p("70 支品牌自製，一天 12 支，6 天拍完（含補拍緩衝）。按「共用材料」分組拍，不按系列順序拍。"),
  spacer(80),
  table([1200, 3600, 4226], [
    ["拍攝日", "拍什麼", "為什麼分在一起"],
    ["D1", "S2 全系列（10 支）＋ 對照組", "只要水和冰塊，最單純，先拍完熟悉模板"],
    ["D2", "S3（10 支）＋ S1 豆漿類", "豆漿、燕麥奶、杏仁奶、椰漿一次備齊"],
    ["D3", "S4（10 支）＋ S1 咖啡茶類", "咖啡機與茶一次架好"],
    ["D4", "S5（10 支）＋ 冷凍品", "果汁機日，水果一次採買，最怕分兩天壞掉"],
    ["D5", "S7（10 支）＋ S8 需冷藏定型者", "定型品前一晚先做好，當天只拍成品"],
    ["D6", "S9（10 支）＋ S6 外景", "熱飲一次架好熱水；S6 移到超商拍"],
  ], { zebra: true, align: [AlignmentType.CENTER] }),
  spacer(160),
  p("S8 剩餘與 S10 排在 D5、D6 的餘量，或安排 D7 補拍日。每支拍完立刻對照配方清單打勾，不要靠記憶。"),

  h2("5.4　後製"),
  p("沿用既有的剪輯 pipeline（安全區、繁體中文字幕渲染、重音字、片尾警語、音訊正規化都已驗證過）。100 支不能一支一支手寫剪輯決策表，因此配方清單會產生結構化資料檔，供批次產生器讀取。"),
  spacer(80),
  p("批次產生器尚未開發——那需要先知道實際素材的檔案結構與剪點習慣，等 D1 拍完、有真實素材可以試跑再開發，比現在憑空設計準確。在那之前，D1 的 10 支手動剪，同時當作模板驗證。"),
];

/* ---------- 6 資源需求 ---------- */

const s6 = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("6　資源需求"),
  rule(),
  h2("6.1　物料成本估算"),
  table([3200, 1400, 1400, 3026], [
    ["項目", "數量", "小計 (NT$)", "說明"],
    ["拍攝用蛋白飲", "約 110 包", "6,050", "100 支＋補拍損耗，以 12 入組每包 55 元計"],
    ["統一搖搖杯", "2 個", "798", "P0016S，含備品"],
    ["生鮮與副材料", "6 個拍攝日", "12,000", "豆漿、植物奶、咖啡、水果、甜點材料，每日約 2,000"],
    ["UGC 獎品", "30 份", "31,770", "每份 1 盒 660 ＋ 搖搖杯 399"],
    [{ text: "合計", bold: true, fill: ZEBRA }, { text: "", fill: ZEBRA }, { text: "50,618", bold: true, fill: ZEBRA }, { text: "", fill: ZEBRA }],
  ]),
  spacer(120),
  note("以官網售價估算。自有商品應以成本價入帳，實際金額會低於此數。本表不含人力、場地、器材租借與廣告投放預算。"),
  spacer(80),
  p("拍攝備料建議優先使用 500g 袋裝（NT$439，每包成本約 31 元，低於隨手包的 55 元），但目前僅拿鐵與黑芝麻兩款有袋裝，其餘口味仍需用隨手包。"),

  h2("6.2　人力與時程"),
  bullet("前製 4 週：6 個拍攝日（含採買、備料、定型品前置）"),
  bullet("發布 20 週：每週 5 支排程發布 ＋ 1 支合集剪輯"),
  bullet("UGC 期 6 週：投稿審核（法規責任在品牌，需指派負責人逐則審）"),
];

/* ---------- 7 風險與待決 ---------- */

const s7 = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("7　風險與待決事項"),
  rule(),
  h2("7.1　庫存：最急，會直接讓企劃打空"),
  p("以下為 Shopify 即時庫存。這些品項在企劃開跑前必須補到位，否則影片導到的是買不到的東西。"),
  spacer(80),
  table([2600, 1700, 1400, 3326], [
    ["品項", "SKU", "現況", "影響"],
    ["黑芝麻牛奶 隨手包", "VG00S1 / VG00S2", "1 入 0、12 入 3", "S10 晚安系列有 4 支用它，整個系列開天窗"],
    ["拿鐵 隨手包 12 入", "VG00L2", "0", "S4 咖啡系列主力口味"],
    ["醇黑可可 隨手包 1 入", "VG00C1", "0", "12 入尚有 192，導購一律指 12 入即可"],
    ["香蕉牛奶 12 入", "VG00B2", "46", "S5、S10 都吃這個口味，46 盒撐不過一週檔期"],
    ["隨手包任選 12 入組", "—", "0", "「自由搭配」是本案最自然的導購終點"],
    ["全素豌豆 4 盒任選組", "—", "0", "客單目標的主力商品"],
  ], { zebra: true }),
  spacer(160),
  p("庫存充足、可以放心主打的是：綜合穀物（2,258）、香蕉牛奶 1 入（774）、抹茶燕麥（738）、奶霧紅茶（1,376）、開心果可可（467）。"),
  spacer(80),
  p([
    run("若補貨來不及：", { bold: true }),
    run("把 S10 晚安系列從第 10 位挪到第 5 位以後再拍，並把黑芝麻的 4 支換成綜合穀物與香蕉牛奶。系列順序可調，斷貨的導購不能救。"),
  ]),

  h2("7.2　搖搖杯是本案的隱形主角"),
  p("100 支影片裡搖搖杯會出現 100 次，但目前白色（0）、紫色（0）、太空灰提環（0）都缺貨，只有白提環（148）、黑提環（150）、綠色（87）有量。拍攝前須先決定主視覺用哪一色並確保它有貨，建議用庫存最深的黑色提環款。"),

  h2("7.3　開心果可可不應放進晚安系列"),
  p("官網把開心果可可歸在「晚安收尾好選擇」，但它含可可，而品牌自己的「零咖啡因組」只收錄香蕉牛奶、黑芝麻牛奶、綜合穀物三款。S10 若要主打「晚上也能喝」，只用這三款，否則等於自己打自己的商品標示。"),

  h2("7.4　本案最可能怎麼死"),
  p("講在前面，比事後檢討有用。"),
  spacer(60),
  bullet("拍到第 30 支就斷。最常見的死法。解法是前製期一次拍完 70 支，不要邊拍邊發——發布是排程，不是持續生產。"),
  bullet("每支都想做得很精緻。100 支不可能支支精品，靠統一模板保底。"),
  bullet("配方越出越獵奇。為了湊數開始出「泡麵加蛋白粉」這種東西會傷品牌。附錄 A 的 100 種已全部盤過，照著拍，不要臨場加。"),
  bullet("UGC 開太早，沒人投稿，變成公開翻車。見 2.2 的門檻與備案。"),
  bullet("庫存打空。見 7.1。"),
];

/* ---------- 8 法規 ---------- */

const q10Ids = recipesDoc.recipes.filter(r => r.warnings.some(w => w.kind === "Q10")).map(r => r.code);
const gabaIds = recipesDoc.recipes.filter(r => r.warnings.some(w => w.kind === "GABA")).map(r => r.code);

const s8 = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("8　法規遵循"),
  rule(),
  p("依《食品安全衛生管理法》第 28 條：食品標示、宣傳或廣告不得有不實、誇張、易生誤解或宣稱醫療效能之情事。100 支影片的字卡全部須通過本節檢查。"),

  h2("8.1　法定警語（必帶，不可省略）"),
  p([run("100 支中有 ", {}), run(`${q10Ids.length + gabaIds.length} 支`, { bold: true }), run(" 需帶法定警語。")]),
  spacer(80),
  table([1600, 7426], [
    ["適用", "警語全文"],
    [`含 Q10（${q10Ids.length} 支）`, "本產品含輔酵素 Q10，十五歲以下孩童、懷孕或哺乳期間婦女，及服用抗凝血藥品之病患不宜食用。"],
    [`含 GABA（${gabaIds.length} 支）`, "本產品含有 GABA，使用本產品應避免同時飲酒或服用降血壓、鎮靜及癲癇等藥物；孕婦、授乳者、嬰幼兒，須諮詢醫師方可使用。"],
  ], { zebra: true }),
  spacer(120),
  note("警語文字取自 Shopify 商品頁，逐字照抄，不得改寫或縮短。適用編號見附錄 B。"),
  spacer(80),
  p("呈現方式：影片片尾 CTA 畫面小字常駐至少 3 秒且落在安全區內；貼文文案結尾固定帶上，不要藏在留言。每支影片需要哪一則警語已逐支標進結構化資料檔，剪輯時直接讀取，不靠人工判斷。"),

  h2("8.2　不可使用的字詞"),
  table([2600, 6426], [
    ["字詞", "原因"],
    ["減脂、瘦身、燃脂、體脂下降", "醫療效能／減肥宣稱"],
    ["抗氧化、抗老、延緩老化", "保健功效宣稱"],
    ["增肌、修復肌肉、練後修復", "生理功能宣稱"],
    ["促進代謝、改善體質、排毒", "醫療效能"],
    ["無糖、零糖、低卡、零負擔", "除非營養標示可證，否則屬不實標示"],
    [{ text: "助眠、好睡、放鬆神經、舒壓", bold: true }, { text: "本案新增風險。S10 晚安系列最容易踩", bold: true }],
    ["取代正餐、一餐只要這杯", "易生誤解，且涉及營養宣稱"],
    ["100% 純可可、純抹茶", "不實。本品為豌豆蛋白飲，可可與抹茶為風味"],
    ["幫助消化、順暢", "保健功效宣稱。輕盈纖果凍的文案不可挪用到蛋白飲"],
  ], { zebra: true }),
  spacer(160),
  p([
    run("商品頁現有的「下午茶的美容補給」與「完美取代高糖手搖飲」兩句都不要沿用到影片", { bold: true }),
    run("：「美容」屬功效性描述，「完美」屬誇大詞。"),
  ]),

  h2("8.3　食安責任"),
  p("教人做東西吃，就要承擔食安揭露責任。加了新鮮水果、豆漿、優格的配方須標「當日飲用完畢」；需冷藏定型的甜點標「冷藏保存，3 日內食用完畢」；保溫瓶外帶標「2 小時內飲用完畢」；熱沖泡標「水溫勿超過 80°C」；氣泡飲標「請勿密封搖晃」。適用編號已標進結構化資料檔。"),

  h2("8.4　UGC 階段的審核"),
  p("開放投稿之後，用字風險從品牌轉移到消費者，但法律責任仍在品牌——官方帳號轉發等同品牌發布。徵集辦法必須明文寫入：投稿不得出現 8.2 的字詞；投稿即授權 AGUGU 於社群管道使用（含剪輯與加字卡）；品牌保留不選用的權利，且轉發前會重新加上必要警語與食安提醒。"),
  spacer(80),
  p([
    run("每一則轉發前須逐則過 8.2 的清單。", { bold: true }),
    run("100 支中有 30 支來自外部，這是本案法規風險最高的一段，建議指派專責審核人。"),
  ]),
];

/* ---------- 9 提請決議 ---------- */

const s9 = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("9　提請決議事項"),
  rule(),
  p("以下六項需在前製期開始前確認，其中第 2、3 項會直接影響能否如期開拍。"),
  spacer(120),
  table([700, 4200, 2000, 2126], [
    ["", "決議事項", "負責", "期限"],
    ["1", "核准本企劃與 20 週檔期（建議 9 月第一週開跑）", "行銷／決策層", "開跑前 5 週"],
    ["2", { text: "核准 7.1 缺貨品項的補貨（黑芝麻、拿鐵 12 入、香蕉牛奶、任選組）", bold: true }, "採購／營運", "開跑前 4 週"],
    ["3", { text: "指定統一搖搖杯色號並確保拍攝期間有貨（建議 P0016S）", bold: true }, "採購／營運", "D1 拍攝前"],
    ["4", "品牌主色與品牌字型檔定案（目前為暫定值，改了 100 支要全部重出）", "設計", "D1 拍攝前"],
    ["5", "核准物料預算約 NT$50,600（不含人力與投放）", "決策層", "開跑前 4 週"],
    ["6", "指派 UGC 投稿審核負責人（法規責任在品牌）", "行銷／法務", "W10 前"],
  ], { zebra: true, align: [AlignmentType.CENTER] }),
  spacer(300),
  p("配方全表見附錄 A，法定警語適用編號見附錄 B。完整執行文件（拍攝流程、後製規格、法規檢查表）已建置於內部版本庫，配方的唯一來源為該處的清單檔，修改後由腳本重新產生結構化資料。"),
];

/* ---------- 附錄 A：100 種配方 ---------- */

const appendixARows = [["編號", "名稱", "口味", "配方與做法", "警語"]];
for (const s of recipesDoc.series) {
  appendixARows.push([
    { text: `${s.id}　${s.title}　#${String(s.from).padStart(3, "0")}–#${String(s.to).padStart(3, "0")}`, span: 5, bold: true, fill: "EDE6D8" },
  ]);
  for (const r of recipesDoc.recipes.filter((x) => x.series === s.id)) {
    appendixARows.push([
      { text: r.code, align: AlignmentType.CENTER },
      r.name,
      r.flavors.map((f) => f.key).join("＋"),
      r.method,
      { text: r.warnings.map((w) => w.kind).join("／") || "—", align: AlignmentType.CENTER },
    ]);
  }
}

const appendixA = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("附錄 A　100 種喝法完整清單"),
  rule(),
  note("共通前提：隨手包 1 包 35g；搖搖杯 700ml、附不鏽鋼攪拌球；液體量以 ml 計，可依濃淡喜好增減。"),
  spacer(80),
  table([900, 1900, 1100, 4026, 1100], appendixARows, { size: 16 }),
  spacer(240),
  h2("拍之前先知道的 5 個雷"),
  p("以下 5 個組合會失敗，不要拍成正式配方。但很適合單獨做一支「我幫你試過了」的影片——這種內容的完成率通常比正常配方高。"),
  spacer(80),
  table([3000, 6026], [
    ["組合", "為什麼會失敗"],
    ["鳳梨、奇異果、木瓜打進去", "這三種水果含蛋白酶，會分解蛋白質，放幾分鐘就變苦、變水，口感全毀"],
    ["檸檬汁、百香果等強酸", "酸會讓蛋白質凝絮，喝起來一顆一顆的沙感"],
    ["氣泡水密封搖", "二氧化碳加上蛋白質的起泡性，開蓋直接噴出來。氣泡一律慢慢倒，不搖"],
    ["80°C 以上的水直接沖粉", "瞬間結塊，攪拌球也救不回來。一律先少量水調糊"],
    ["搖搖杯裝熱飲鎖緊", "密閉容器裝熱液體，內壓升高會噴。熱飲用馬克杯，或杯蓋不要完全鎖死"],
  ], { zebra: true }),
];

/* ---------- 附錄 B：口味與警語對照 ---------- */

const flavorRows = [];
const seen = new Set();
for (const r of recipesDoc.recipes) {
  for (const f of r.flavors) {
    if (f.key === "任一" || seen.has(f.key)) continue;
    seen.add(f.key);
    flavorRows.push([
      f.key,
      f.name,
      `${f.sku_1} / ${f.sku_12}`,
      `${f.protein_g} g`,
      recipesDoc.recipes.some(x => x.flavors.some(y => y.key === f.key) && x.warnings.length)
        ? (f.key === "可可" ? "Q10" : "GABA") : "—",
    ]);
  }
}

const appendixB = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("附錄 B　口味對照與警語適用編號"),
  rule(),
  h2("B.1　口味對照表"),
  table([1200, 2800, 2200, 1300, 1526], [
    ["簡稱", "商品全名（隨手包）", "SKU（1 入／12 入）", "蛋白質", "警語"],
    ...flavorRows,
  ], { zebra: true, size: 17, align: [AlignmentType.CENTER, undefined, undefined, AlignmentType.CENTER, AlignmentType.CENTER] }),
  spacer(120),
  note("蛋白質克數取自 Shopify 商品頁。字卡標示須與該支實際使用的口味一致。"),

  h2("B.2　需帶 Q10 警語的編號"),
  p(q10Ids.join("　"), { size: 19 }),
  note("本產品含輔酵素 Q10，十五歲以下孩童、懷孕或哺乳期間婦女，及服用抗凝血藥品之病患不宜食用。"),

  h2("B.3　需帶 GABA 警語的編號"),
  p(gabaIds.join("　"), { size: 19 }),
  note("本產品含有 GABA，使用本產品應避免同時飲酒或服用降血壓、鎮靜及癲癇等藥物；孕婦、授乳者、嬰幼兒，須諮詢醫師方可使用。"),
  spacer(120),
  p("混口味的配方按實際用到的口味判斷：#039（抹茶＋可可）只需 Q10；#100（香蕉＋芝麻）兩款都含 GABA，帶一次即可。#011 與 #018 標示為「任一口味」，拍攝時實際選了哪一款，就跟著那款的警語走。"),
];

/* ---------- 組裝 ---------- */

const doc = new Document({
  creator: "AGUGU",
  title: "蛋白飲的 100 種喝法｜內部提案書",
  description: "20 週社群內容企劃提案",
  styles: {
    default: {
      document: { run: { font: FONT, size: 21, color: INK }, paragraph: { spacing: { line: 300 } } },
      heading1: { run: { font: FONT, size: 30, bold: true, color: INK } },
      heading2: { run: { font: FONT, size: 24, bold: true, color: INK } },
    },
  },
  numbering: {
    config: [{
      reference: "dot",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 360, hanging: 200 } } },
      }],
    }],
  },
  sections: [{
    properties: { page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: ["AGUGU｜蛋白飲的 100 種喝法　內部提案書　—　", PageNumber.CURRENT], size: 16, color: MUTED })],
        })],
      }),
    },
    children: [
      ...cover, ...toc, ...s1, ...s2, ...s3, ...s5, ...s6, ...s7, ...s8, ...s9,
      ...appendixA, ...appendixB,
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = process.argv[2] || path.join(REPO, "docs/100-ways/AGUGU_100種喝法_內部提案書.docx");
  fs.writeFileSync(out, buf);
  console.log(`已產生 ${out}（${(buf.length / 1024).toFixed(0)} KB）`);
  console.log(`配方 ${recipesDoc.recipes.length} 筆、系列 ${recipesDoc.series.length} 個、需帶警語 ${q10Ids.length + gabaIds.length} 支`);
});
