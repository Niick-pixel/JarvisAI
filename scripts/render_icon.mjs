// Renders web/src/brand/jarvis.svg to packaging/icon/jarvis-<size>.png, the frames of the app
// icon. Run after changing the SVG, then commit the PNGs; packaging/make_icon.py packs them into
// jarvis.ico at build time without needing a browser.
//
//   NODE_PATH=$(npm root -g) node scripts/render_icon.mjs      (needs playwright + Chromium)
//
// Below 48 px the shapes marked class="detail" are dropped: at taskbar size the light strips and
// slots only blur, and the silhouette - six handles, one red eye - is what has to read.
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const { chromium } = createRequire(import.meta.url)("playwright");
const SIZES = [16, 24, 32, 48, 64, 128, 256];
const svg = readFileSync(new URL("../web/src/brand/jarvis.svg", import.meta.url), "utf8");
const small = (text) =>
  text.replace(/<g class="detail"[\s\S]*?<\/g>/g, "").replace(/<[a-z]+ class="detail"[^>]*\/>/g, "");

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || "/opt/pw-browsers/chromium" });
for (const size of SIZES) {
  const page = await browser.newPage({ viewport: { width: size, height: size } });
  const body = (size < 48 ? small(svg) : svg).replace("<svg ", `<svg width="${size}" height="${size}" `);
  await page.setContent(`<body style="margin:0;background:transparent">${body}</body>`);
  const out = new URL(`../packaging/icon/jarvis-${size}.png`, import.meta.url);
  await page.screenshot({ path: out.pathname, omitBackground: true, clip: { x: 0, y: 0, width: size, height: size } });
  await page.close();
}
await browser.close();
console.log(`rendered ${SIZES.length} sizes`);
