import { chromium } from "playwright";

const URL = "https://www.klook.com/ko/activity/251-lotte-world-seoul/";

const browser = await chromium.launch({
  headless: false,
  channel: "chrome",
  args: [
    "--no-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--window-size=1280,900",
    "--start-maximized",
  ],
});

const ctx = await browser.newContext({
  userAgent:
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
  locale: "ko-KR",
  timezoneId: "Asia/Seoul",
  viewport: { width: 1280, height: 900 },
  extraHTTPHeaders: { "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8" },
});

await ctx.addInitScript(() => {
  Object.defineProperty(navigator, "webdriver", { get: () => undefined });
  Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3, 4, 5] });
  window.chrome = { runtime: {} };
});

const page = await ctx.newPage();

// 홈페이지 먼저 방문 (쿠키/세션 확보)
console.error("Step 1: 홈페이지 방문...");
await page.goto("https://www.klook.com/ko/", { waitUntil: "domcontentloaded", timeout: 30000 });
await page.waitForTimeout(5000);
console.error("  홈 cookies:", (await ctx.cookies()).map(c => c.name).join(", "));

// DataDome 챌린지 대기
await page.waitForTimeout(3000);

console.error("Step 2: 상세페이지 방문...");
const resp = await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 30000 });
console.error("status:", resp.status());
// 챌린지 자동 해결 대기
await page.waitForTimeout(8000);

const html = await page.content();
console.error("html length:", html.length);
console.error("title:", await page.title());
console.error("cookies:", (await ctx.cookies()).map(c => c.name).join(", "));

// DataDome 차단 여부
if (html.length < 5000) {
  console.error("BLOCKED:", html.slice(0, 400));
  await browser.close();
  process.exit(1);
}

// __NEXT_DATA__ 추출
const ndMatch = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
if (ndMatch) {
  console.error("__NEXT_DATA__ FOUND");
  const data = JSON.parse(ndMatch[1]);
  const props = data?.props?.pageProps ?? {};
  console.error("pageProps keys:", Object.keys(props).slice(0, 30).join(", "));
  // 전체 pageProps를 stdout으로 출력
  console.log(JSON.stringify(props, null, 2));
} else {
  console.error("__NEXT_DATA__ NOT FOUND");
  // JSON-LD 시도
  const ldMatches = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)];
  console.error("JSON-LD count:", ldMatches.length);
  const lds = ldMatches.map((m) => { try { return JSON.parse(m[1]); } catch { return null; } }).filter(Boolean);
  console.log(JSON.stringify(lds, null, 2));
}

await browser.close();
