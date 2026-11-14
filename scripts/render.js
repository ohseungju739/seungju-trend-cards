#!/usr/bin/env node
// 소식 JSON → 인스타그램 카드 PNG (1080x1350, 4:5)
// 사용법: node scripts/render.js data/2026-11-14.json [출력폴더]
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const W = 1080;
const H = 1350;
const root = path.resolve(__dirname, '..');

const esc = (s) =>
  String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const br = (s) => esc(s).replace(/\n/g, '<br>');

function fontCss() {
  const dir = path.join(root, 'node_modules/pretendard/dist/web/static/woff2');
  if (!fs.existsSync(dir)) {
    throw new Error('글꼴이 없습니다. 먼저 `npm install`을 실행하세요.');
  }
  return [
    [500, 'Medium'],
    [700, 'Bold'],
    [800, 'ExtraBold'],
  ]
    .map(([weight, name]) => {
      const b64 = fs.readFileSync(path.join(dir, `Pretendard-${name}.woff2`)).toString('base64');
      return `@font-face{font-family:'Pretendard';font-weight:${weight};src:url(data:font/woff2;base64,${b64}) format('woff2');}`;
    })
    .join('\n');
}

const css = `
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:${W}px;height:${H}px}
body{font-family:'Pretendard',sans-serif;font-weight:500;color:#1b1b1f;background:#f6f1e8;
  word-break:keep-all;overflow-wrap:break-word;-webkit-font-smoothing:antialiased}
.card{width:${W}px;height:${H}px;padding:96px 88px 80px;display:flex;flex-direction:column;position:relative}
.top{display:flex;justify-content:space-between;align-items:center;font-size:30px;font-weight:700;letter-spacing:.02em}
.brand{color:#e4572e}
.page{color:#8a8478;font-variant-numeric:tabular-nums}
.foot{margin-top:auto;font-size:26px;color:#8a8478;border-top:2px solid #ddd5c6;padding-top:28px;line-height:1.4}

.cover{background:#1b1b1f;color:#f6f1e8}
.cover .page{color:#77736b}
.cover .mid{margin-top:auto;margin-bottom:auto}
.cover .period{display:inline-block;font-size:34px;font-weight:700;color:#1b1b1f;background:#e4572e;
  padding:12px 26px;border-radius:999px;font-variant-numeric:tabular-nums}
.cover h1{font-size:112px;line-height:1.16;font-weight:800;letter-spacing:-.03em;margin-top:44px}
.cover .sub{font-size:42px;color:#b9b3a7;margin-top:40px}
.cover .foot{border-top-color:#3a3a40;color:#77736b}

.meta{display:flex;gap:16px;align-items:center;margin-top:92px}
.date{font-size:34px;font-weight:700;color:#e4572e}
.tag{font-size:28px;font-weight:700;border:2.5px solid #1b1b1f;border-radius:999px;padding:6px 22px}
h2{font-size:78px;line-height:1.2;font-weight:800;letter-spacing:-.03em;margin-top:36px}
ul{list-style:none;margin-top:64px;display:flex;flex-direction:column;gap:38px}
li{font-size:42px;line-height:1.45;padding-left:44px;position:relative}
li::before{content:'';position:absolute;left:0;top:22px;width:18px;height:18px;border-radius:50%;background:#e4572e}

.closing h2{margin-top:92px}
.closing ul{gap:30px}
.closing li{font-size:34px}
.closing li::before{top:16px;width:14px;height:14px}
.note{margin-top:64px;font-size:34px;line-height:1.5;background:#ebe3d3;border-radius:28px;padding:36px 40px}
`;

function buildCards(data) {
  const total = data.items.length + 2;
  const top = (n) =>
    `<div class="top"><span class="brand">CLAUDE WEEKLY</span><span class="page">${n} / ${total}</span></div>`;
  const cards = [];

  cards.push(`<div class="card cover">${top(1)}
    <div class="mid">
      <span class="period">${esc(data.period)}</span>
      <h1>${br(data.title)}</h1>
      <p class="sub">${esc(data.subtitle)}</p>
    </div>
    <div class="foot">옆으로 넘겨서 확인하세요 →</div>
  </div>`);

  data.items.forEach((it, i) => {
    cards.push(`<div class="card">${top(i + 2)}
      <div class="meta"><span class="date">${esc(it.date)}</span><span class="tag">${esc(it.tag)}</span></div>
      <h2>${br(it.headline)}</h2>
      <ul>${it.points.map((p) => `<li>${esc(p)}</li>`).join('')}</ul>
      <div class="foot">출처 · ${esc(it.source)}</div>
    </div>`);
  });

  const c = data.closing;
  cards.push(`<div class="card closing">${top(total)}
    <h2>${br(c.headline)}</h2>
    <ul>${c.lines.map((l) => `<li>${esc(l)}</li>`).join('')}</ul>
    <p class="note">${esc(c.note)}</p>
    <div class="foot">매주 월요일, 새 소식을 정리합니다</div>
  </div>`);

  return cards;
}

async function main() {
  const input = process.argv[2];
  if (!input) {
    console.error('사용법: node scripts/render.js <소식.json> [출력폴더]');
    process.exit(1);
  }
  const data = JSON.parse(fs.readFileSync(input, 'utf8'));
  const outDir = process.argv[3] || path.join(root, 'output', path.basename(input, '.json'));
  fs.mkdirSync(outDir, { recursive: true });

  const fonts = fontCss();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  const cards = buildCards(data);
  for (let i = 0; i < cards.length; i++) {
    await page.setContent(
      `<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>${fonts}${css}</style></head><body>${cards[i]}</body></html>`
    );
    await page.evaluate(() => document.fonts.ready);
    const overflow = await page.evaluate(() => {
      const el = document.querySelector('.card');
      return el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth;
    });
    if (overflow) console.warn(`경고: ${i + 1}번 카드의 내용이 넘칩니다. 문장을 줄여 주세요.`);
    const file = path.join(outDir, `card-${String(i + 1).padStart(2, '0')}.png`);
    await page.screenshot({ path: file });
    console.log(file);
  }
  await browser.close();
}

main().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
