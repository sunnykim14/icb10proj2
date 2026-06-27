/**
 * 실제 Chrome 사용자 프로필 사용 - 기존 DataDome 세션 쿠키 활용.
 * 또는 네트워크 요청을 캡처해서 Klook이 내부적으로 호출하는 API를 찾는다.
 */
import { chromium } from "playwright";
import { resolve } from "path";
import { homedir } from "os";

const ACTIVITY_URL = "https://www.klook.com/ko/activity/251-lotte-world-seoul/";

// Chrome 실제 사용자 데이터 디렉토리 (기존 쿠키/로그인 상태 포함)
const userDataDir = resolve(homedir(), "AppData", "Local", "Google", "Chrome", "User Data");
console.error("User data dir:", userDataDir);

const browser = await chromium.launchPersistentContext(userDataDir, {
  headless: false,
  channel: "chrome",
  args: [
    "--no-sandbox",
    "--profile-directory=Default",
    "--disable-blink-features=AutomationControlled",
  ],
  userAgent:
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
  locale: "ko-KR",
  viewport: { width: 1280, height: 900 },
});

const page = await browser.newPage();

// 네트워크 요청 캡처 - Klook 내부 API 찾기
const apiCalls = [];
page.on("request", (req) => {
  const url = req.url();
  if (url.includes("klook.com/v") || url.includes("klook.com/api") || url.includes("klook.com/graphql")) {
    apiCalls.push({ method: req.method(), url: url.slice(0, 120) });
  }
});

page.on("response", async (res) => {
  const url = res.url();
  if ((url.includes("klook.com/v") || url.includes("klook.com/api")) && res.status() === 200) {
    try {
      const ct = res.headers()["content-type"] || "";
      if (ct.includes("json")) {
        const body = await res.json().catch(() => null);
        if (body && body.result) {
          console.error(`[API] ${url.slice(url.indexOf("/v"))}`);
        }
      }
    } catch {}
  }
});

console.error("페이지 방문 중...");
try {
  const resp = await page.goto(ACTIVITY_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  console.error("status:", resp.status());
  await page.waitForTimeout(8000);

  const html = await page.content();
  console.error("html length:", html.length);

  if (html.length > 5000) {
    const ndMatch = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
    if (ndMatch) {
      const props = JSON.parse(ndMatch[1])?.props?.pageProps ?? {};
      console.error("SUCCESS! pageProps keys:", Object.keys(props).join(", "));
      console.log(JSON.stringify({ status: "ok", props }, null, 2));
    }
  } else {
    console.error("BLOCKED. html:", html.slice(0, 200));
  }

  // 캡처된 API 목록 출력
  console.error("\n캡처된 Klook API 호출:");
  for (const c of apiCalls) {
    console.error(" ", c.method, c.url);
  }
} catch (e) {
  console.error("에러:", e.message);
}

await browser.close();
