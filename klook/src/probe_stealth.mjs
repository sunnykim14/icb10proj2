import { chromium as base } from "playwright-extra";
import StealthPlugin from "playwright-extra-plugin-stealth";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
base.use(StealthPlugin());

const URL = "https://www.klook.com/ko/activity/251-lotte-world-seoul/";

const browser = await base.launch({
  headless: true,
  channel: "chrome",
  args: ["--no-sandbox"],
});

const ctx = await browser.newContext({
  userAgent:
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
  locale: "ko-KR",
  timezoneId: "Asia/Seoul",
  viewport: { width: 1280, height: 900 },
  extraHTTPHeaders: { "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8" },
});

const page = await ctx.newPage();

// 홈 먼저
console.error("[1] 홈페이지...");
await page.goto("https://www.klook.com/ko/", { waitUntil: "domcontentloaded", timeout: 30000 });
await page.waitForTimeout(6000);
console.error("    cookies:", (await ctx.cookies()).map((c) => c.name).join(", "));

// 상세페이지
console.error("[2] 상세페이지...");
const resp = await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 30000 });
console.error("    status:", resp.status());
await page.waitForTimeout(8000);

const html = await page.content();
console.error("    html length:", html.length, "| title:", await page.title());

if (html.length < 5000) {
  console.error("BLOCKED:", html.slice(0, 300));
  await browser.close();
  process.exit(1);
}

// __NEXT_DATA__ 추출
const ndMatch = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
if (ndMatch) {
  console.error("__NEXT_DATA__ FOUND - pageProps keys:");
  const data = JSON.parse(ndMatch[1]);
  const props = data?.props?.pageProps ?? {};
  console.error(Object.keys(props).join(", "));
  // stdout으로 JSON 출력
  console.log(JSON.stringify({ source: "NEXT_DATA", data: props }, null, 2));
}

await browser.close();
