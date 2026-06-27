/**
 * Naver Whale 실제 프로필로 Klook 상세페이지 접근 + 내부 API 캡처.
 */
import { chromium } from "playwright";

const WHALE_EXE = "C:\\Program Files\\Naver\\Naver Whale\\Application\\whale.exe";
const WHALE_DATA = "C:\\Users\\admin\\AppData\\Local\\Naver\\Naver Whale\\User Data";
const ACTIVITY_URL = "https://www.klook.com/ko/activity/251-lotte-world-seoul/";

const ctx = await chromium.launchPersistentContext(WHALE_DATA, {
  executablePath: WHALE_EXE,
  headless: false,
  args: [
    "--no-sandbox",
    "--profile-directory=Default",
    "--disable-blink-features=AutomationControlled",
    "--window-size=1280,900",
  ],
  userAgent:
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Whale/4.29.282.14 Safari/537.36",
  locale: "ko-KR",
  timezoneId: "Asia/Seoul",
  viewport: { width: 1280, height: 900 },
  extraHTTPHeaders: { "Accept-Language": "ko-KR,ko;q=0.9" },
});

// 스텔스 초기화
await ctx.addInitScript(() => {
  Object.defineProperty(navigator, "webdriver", { get: () => undefined, configurable: true });
  window.chrome = { runtime: { id: undefined } };
  Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3, 4, 5] });
});

const page = await ctx.newPage();

// Klook 내부 API 요청 캡처
const capturedApis = [];
page.on("request", (req) => {
  const url = req.url();
  if (url.includes("/v1/") || url.includes("/v2/") || url.includes("/api/")) {
    if (url.includes("klook.com")) {
      capturedApis.push({ method: req.method(), url });
    }
  }
});

const capturedResponses = {};
page.on("response", async (res) => {
  const url = res.url();
  if (!url.includes("klook.com")) return;
  const ct = res.headers()["content-type"] || "";
  if (!ct.includes("json")) return;
  if (!url.includes("/v1/") && !url.includes("/v2/") && !url.includes("/api/")) return;
  try {
    const body = await res.json();
    if (body && (body.result || body.data || body.success)) {
      const key = url.replace(/https?:\/\/[^/]+/, "").split("?")[0];
      capturedResponses[key] = { url, status: res.status(), body };
    }
  } catch {}
});

console.error("[1] 홈 방문...");
try {
  await page.goto("https://www.klook.com/ko/", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(4000);
} catch (e) {
  console.error("  홈 방문 에러:", e.message);
}

console.error("[2] 상세페이지 방문...");
let resp;
try {
  resp = await page.goto(ACTIVITY_URL, { waitUntil: "networkidle", timeout: 30000 });
} catch {
  resp = await page.goto(ACTIVITY_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
}
console.error("  status:", resp?.status());
await page.waitForTimeout(6000);

const html = await page.content();
const title = await page.title();
console.error("  html length:", html.length, "| title:", title);

if (html.length > 5000) {
  // __NEXT_DATA__ 추출
  const ndMatch = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
  if (ndMatch) {
    const props = JSON.parse(ndMatch[1])?.props?.pageProps ?? {};
    console.error("SUCCESS! pageProps keys:", Object.keys(props).slice(0, 20).join(", "));
    console.log(JSON.stringify({ source: "NEXT_DATA", props }, null, 2));
  } else {
    // JSON-LD 시도
    const lds = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
      .map((m) => { try { return JSON.parse(m[1]); } catch { return null; } })
      .filter(Boolean);
    console.error("JSON-LD count:", lds.length);
    if (lds.length > 0) console.log(JSON.stringify({ source: "LD", lds }, null, 2));
  }
} else {
  console.error("BLOCKED:", html.slice(0, 300));
}

console.error("\n캡처된 Klook API:");
for (const [k, v] of Object.entries(capturedResponses)) {
  console.error(" ", v.status, k);
}
// API 목록을 stdout으로 출력
console.log(JSON.stringify({ captured_apis: capturedApis.map((a) => a.url) }, null, 2));

await ctx.close();
