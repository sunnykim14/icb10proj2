/**
 * CDP로 automation 신호 제거 후 Klook 상세페이지 접근.
 * headless=false + 실제 Chrome + CDP stealth
 */
import { chromium } from "playwright";
import { readFileSync } from "fs";

const ACTIVITY_URL = "https://www.klook.com/ko/activity/251-lotte-world-seoul/";

const browser = await chromium.launch({
  headless: false,
  executablePath: "C:\\Program Files\\Naver\\Naver Whale\\Application\\whale.exe",
  args: [
    "--no-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--window-size=1280,900",
  ],
});

const ctx = await browser.newContext({
  userAgent:
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
  locale: "ko-KR",
  timezoneId: "Asia/Seoul",
  viewport: { width: 1280, height: 900 },
  extraHTTPHeaders: {
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
  },
});

// 종합 스텔스 스크립트
await ctx.addInitScript(() => {
  // 1) webdriver 제거
  delete Object.getPrototypeOf(navigator).webdriver;
  Object.defineProperty(navigator, "webdriver", { get: () => undefined, configurable: true });

  // 2) Chrome 런타임 추가
  window.chrome = {
    runtime: { id: undefined },
    loadTimes: () => ({}),
    csi: () => ({}),
  };

  // 3) 플러그인 목록
  Object.defineProperty(navigator, "plugins", {
    get: () => {
      const arr = [
        { name: "Chrome PDF Plugin", filename: "internal-pdf-viewer", description: "Portable Document Format" },
        { name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai", description: "" },
        { name: "Native Client", filename: "internal-nacl-plugin", description: "" },
      ];
      arr.__proto__ = PluginArray.prototype;
      return arr;
    },
    configurable: true,
  });

  // 4) 언어 설정
  Object.defineProperty(navigator, "languages", { get: () => ["ko-KR", "ko", "en-US", "en"] });

  // 5) hardware concurrency
  Object.defineProperty(navigator, "hardwareConcurrency", { get: () => 8 });

  // 6) permissions
  const originalQuery = window.navigator.permissions.query;
  window.navigator.permissions.query = (params) =>
    params.name === "notifications"
      ? Promise.resolve({ state: Notification.permission })
      : originalQuery(params);
});

const page = await ctx.newPage();

// CDP를 통한 추가 stealth
const cdp = await ctx.newCDPSession(page);
await cdp.send("Page.addScriptToEvaluateOnNewDocument", {
  source: `
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
  `,
});

console.error("[1] 홈 방문...");
await page.goto("https://www.klook.com/ko/", { waitUntil: "domcontentloaded", timeout: 30000 });
await page.waitForTimeout(7000);
const homeCookies = (await ctx.cookies()).map((c) => c.name);
console.error("    쿠키:", homeCookies.join(", "));

console.error("[2] 상세페이지 방문...");
const resp = await page.goto(ACTIVITY_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
console.error("    status:", resp.status());
await page.waitForTimeout(10000);

const html = await page.content();
const title = await page.title();
console.error("    html length:", html.length, "| title:", title);

if (html.length < 5000) {
  console.error("BLOCKED:", html.slice(0, 500));
  await browser.close();
  process.exit(1);
}

const ndMatch = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
if (ndMatch) {
  const props = JSON.parse(ndMatch[1])?.props?.pageProps ?? {};
  console.error("SUCCESS! pageProps keys:", Object.keys(props).join(", "));
  console.log(JSON.stringify({ status: "ok", props }, null, 2));
} else {
  console.error("__NEXT_DATA__ not found. Title:", title);
  // HTML 일부 출력
  console.log(JSON.stringify({ status: "no_next_data", html_snippet: html.slice(0, 2000) }));
}

await browser.close();
