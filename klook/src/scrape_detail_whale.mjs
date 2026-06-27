/**
 * Whale CDP로 Klook 상세페이지 접근 → 내부 API 응답을 캡처해서 저장.
 * 사용법: node scrape_detail_whale.mjs <input_json> <output_json> [port]
 */
import { chromium } from "playwright";
import { readFileSync, writeFileSync } from "fs";

const [, , INPUT, OUTPUT, PORT = "9222"] = process.argv;
const activities = JSON.parse(readFileSync(INPUT, "utf8"));

const browser = await chromium.connectOverCDP(`http://localhost:${PORT}`);
const contexts = browser.contexts();
const ctx = contexts.length > 0 ? contexts[0] : await browser.newContext();

const results = [];

// 관심 API 경로 패턴 (activity ID를 포함한 것 + 특정 서비스)
const INTEREST_PATTERNS = [
  "get_platform_overview",
  "detail_page_dynamic_info",
  "get_activity_faq_section",
  "get_package_option_sources",
  "get_package_card_sku_info",
  "activity_reviews_list",
  "images/show",
  "images/get",
  "get_spu_list_section",
  "get_sgculture_pass_section",
  "get_standard_pass_activity_info",
];

for (let i = 0; i < activities.length; i++) {
  const { activity_id, url } = activities[i];
  // /en-US/ → /ko/ 변환
  const koUrl = url.replace("/en-US/", "/ko/");
  process.stderr.write(`\n[activity ${activity_id}] (${i+1}/${activities.length}) ${koUrl}\n`);

  // 3페이지마다 홈 방문으로 DataDome 세션 갱신
  if (i > 0 && i % 3 === 0) {
    process.stderr.write(`  [세션 갱신] 홈 방문...\n`);
    const homePage = await ctx.newPage();
    try {
      await homePage.goto("https://www.klook.com/ko/", { waitUntil: "domcontentloaded", timeout: 20000 });
      await homePage.waitForTimeout(4000);
    } catch {}
    await homePage.close();
    await new Promise((r) => setTimeout(r, 2000));
  }

  const capturedApis = {};   // path → JSON body
  const page = await ctx.newPage();

  // 응답 캡처
  page.on("response", async (res) => {
    const u = res.url();
    if (!u.includes("klook.com")) return;
    const ct = res.headers()["content-type"] || "";
    if (!ct.includes("json")) return;
    const path = u.replace(/https?:\/\/[^/]+/, "").replace(/\?.*$/, "");
    const interested = INTEREST_PATTERNS.some((p) => path.includes(p));
    if (!interested) return;
    try {
      const body = await res.json();
      if (body) capturedApis[path] = body;
    } catch {}
  });

  let record = { activity_id, url: koUrl, status: "error", apis: {} };

  try {
    const resp = await page.goto(koUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    const httpStatus = resp?.status();
    const htmlLen = (await page.content()).length;
    process.stderr.write(`  HTTP ${httpStatus}, html=${htmlLen}\n`);

    if (httpStatus === 403 || htmlLen < 3000) {
      // DataDome 차단 - 홈 방문 후 재시도
      process.stderr.write(`  차단 감지. 홈 방문 후 재시도...\n`);
      await page.goto("https://www.klook.com/ko/", { waitUntil: "domcontentloaded", timeout: 20000 });
      await page.waitForTimeout(5000);
      const resp2 = await page.goto(koUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
      process.stderr.write(`  재시도 status=${resp2?.status()}, html=${(await page.content()).length}\n`);
    }

    // API 완전 로딩 대기
    await page.waitForTimeout(7000);

    const finalHtml = await page.content();
    const finalStatus = finalHtml.length > 5000 ? "ok" : `http_${httpStatus}`;
    const apiKeys = Object.keys(capturedApis);
    process.stderr.write(`  captured APIs (${apiKeys.length}): ${apiKeys.map(k => k.split("/").slice(-2).join("/")).join(", ")}\n`);

    record = { activity_id, url: koUrl, status: finalStatus, apis: capturedApis };
  } catch (e) {
    record.error = e.message;
    process.stderr.write(`  ERROR: ${e.message}\n`);
  }

  results.push(record);
  await page.close();
  await new Promise((r) => setTimeout(r, 3000));
}

await browser.close();
writeFileSync(OUTPUT, JSON.stringify(results, null, 2), "utf8");
process.stderr.write(`\n완료: ${results.length}건 → ${OUTPUT}\n`);
