"""
Klook 상위 10개 상품 상세페이지 수집 → product_details 테이블 저장.

방식:
  1. Whale을 --remote-debugging-port로 subprocess 실행
  2. Node.js playwright가 CDP 연결 → 상세페이지 로드 → 내부 API 응답 캡처
  3. 캡처된 JSON API 응답에서 필드 추출 → SQLite 저장
  4. v_product_detail 조인 뷰 생성
"""

import json
import os
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "klook.db"
SRC_DIR = Path(__file__).parent
WHALE_EXE = r"C:\Program Files\Naver\Naver Whale\Application\whale.exe"
WHALE_PORT = 9224
NODE_SCRIPT = SRC_DIR / "scrape_detail_whale.mjs"


# ── DB 스키마 ─────────────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS product_details")
    conn.execute("""
        CREATE TABLE product_details (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id         INTEGER UNIQUE,
            detail_url          TEXT,
            http_status         TEXT,
            title               TEXT,
            description         TEXT,
            highlights          TEXT,
            inclusions          TEXT,
            exclusions          TEXT,
            duration            TEXT,
            meeting_point       TEXT,
            cancellation_policy TEXT,
            important_info      TEXT,
            photos_json         TEXT,
            faq_json            TEXT,
            packages_json       TEXT,
            reviews_json        TEXT,
            price_min           TEXT,
            price_currency      TEXT,
            review_star         REAL,
            review_count        TEXT,
            raw_apis_json       TEXT,
            collected_at        TEXT
        )
    """)
    conn.execute("DROP VIEW IF EXISTS v_product_detail")
    conn.execute("""
        CREATE VIEW v_product_detail AS
        SELECT
            p.id,
            p.activity_id,
            p.page_num,
            p.query_keyword,
            p.title            AS search_title,
            p.city,
            p.category,
            p.selling_price,
            p.review_star      AS search_review_star,
            p.review_count     AS search_review_count,
            p.tags,
            p.deep_link,
            d.detail_url,
            d.http_status,
            d.title            AS detail_title,
            d.description,
            d.highlights,
            d.inclusions,
            d.exclusions,
            d.duration,
            d.meeting_point,
            d.cancellation_policy,
            d.important_info,
            d.photos_json,
            d.faq_json,
            d.packages_json,
            d.reviews_json,
            d.price_min,
            d.price_currency,
            d.review_star      AS detail_review_star,
            d.review_count     AS detail_review_count,
            d.collected_at
        FROM products p
        LEFT JOIN product_details d ON p.activity_id = d.activity_id
    """)
    conn.commit()


# ── Whale 실행 ────────────────────────────────────────────────────────────────

def launch_whale(port: int) -> subprocess.Popen:
    tmp_dir = Path(tempfile.gettempdir()) / f"whale_cdp_{port}"
    tmp_dir.mkdir(exist_ok=True)
    cmd = [
        WHALE_EXE,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={tmp_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-sync",
        "--new-window",
        "about:blank",
    ]
    print(f"  Whale 실행: port={port}")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(20):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=1)
            print(f"  Whale CDP 준비 (pid={proc.pid})")
            return proc
        except Exception:
            continue
    raise RuntimeError(f"Whale이 {port}번 포트에서 응답하지 않습니다.")


# ── Node.js 스크래퍼 실행 ─────────────────────────────────────────────────────

def run_node_scraper(activities: list[dict], port: int) -> list[dict]:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(activities, f, ensure_ascii=False)
        in_path = f.name
    out_path = in_path.replace(".json", "_out.json")

    cmd = ["node", str(NODE_SCRIPT), in_path, out_path, str(port)]
    print(f"  Node.js 실행...")
    subprocess.run(cmd, text=True, encoding="utf-8", errors="replace", timeout=300)

    os.unlink(in_path)
    if not Path(out_path).exists():
        return []
    with open(out_path, encoding="utf-8") as f:
        data = json.load(f)
    os.unlink(out_path)
    return data


# ── API 응답 파싱 ─────────────────────────────────────────────────────────────

def _jstr(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return json.dumps(val, ensure_ascii=False)


def _find_api(apis: dict, *keywords) -> dict:
    """키워드를 포함하는 첫 번째 API 응답 반환."""
    for key, val in apis.items():
        if all(kw in key for kw in keywords):
            return val
    return {}


def _render_obj_texts(render_obj: list) -> list[str]:
    """render_obj 배열에서 content 텍스트를 추출."""
    texts = []
    for item in render_obj or []:
        c = item.get("content", "")
        if c:
            texts.append(c)
    return texts


def _extract_from_spu_sections(sections: list) -> dict:
    """spu_list_section.first_spu_detail.sections 에서 핵심 필드 추출."""
    result = {
        "inclusions": [], "exclusions": [], "important_info": [],
        "meeting_point": "", "cancellation_policy": "", "usage_info": "",
    }
    FIELD_MAP = {
        "aid_spu_whats_include": "inclusions",
        "aid_spu_not_include": "exclusions",
        "eligibility": "important_info",
        "aid_spu_additional_information": "important_info",
        "location": "meeting_point",
        "group_usage_validity": "cancellation_policy",
        "aid_voucher_type_desc": "usage_info",
    }
    for sec in sections or []:
        for comp in sec.get("components", []):
            data = comp.get("data", {})
            field_key = (data.get("props") or {}).get("field_key", "")
            render_obj = data.get("render_obj") or []
            texts = _render_obj_texts(render_obj)
            target = FIELD_MAP.get(field_key)
            if target is None:
                continue
            if target in ("inclusions", "exclusions", "important_info"):
                result[target].extend(texts)
            elif texts:
                result[target] = texts[0]
    return result


def extract_detail(activity_id: int, url: str, status: str, apis: dict) -> dict:
    now = datetime.now().isoformat(timespec="seconds")

    # ── API별 result 추출 ──────────────────────────────────────────────────────
    spu_body = _find_api(apis, "get_spu_list_section")
    spu_result = spu_body.get("result", {}) if spu_body else {}
    first_spu = spu_result.get("first_spu_detail", {})
    spu_basic = first_spu.get("spu_basic", {})
    spu_sections = first_spu.get("sections", [])
    icon_items = first_spu.get("icon_items", [])  # 빠른 확인 뱃지 (예약 즉시 확정 등)

    faq_body = _find_api(apis, "get_activity_faq_section")
    faq_result = faq_body.get("result", {}) if faq_body else {}
    activity_faq = faq_result.get("activity_faq") or {}
    faqs = activity_faq.get("faq") or []

    pkg_body = _find_api(apis, "get_package_option_sources")
    pkg_result = pkg_body.get("result", {}) if pkg_body else {}
    packages = pkg_result.get("packages") or []
    activity_closer_price = pkg_result.get("activity_closer_price") or {}
    spu_groups = pkg_result.get("spu_group_info") or spu_result.get("spu_group_info") or []

    rev_body = _find_api(apis, "activity_reviews_list")
    rev_result = rev_body.get("result", {}) if rev_body else {}
    reviews = rev_result.get("item") or []

    ov_body = _find_api(apis, "get_platform_overview")
    ov_result = ov_body.get("result", {}) if ov_body else {}
    rating_info = ov_result.get("rating_info") or {}
    ov_reviews = (ov_result.get("reviews") or {}).get("review_list") or []

    img_body = _find_api(apis, "images/show")
    img_result = img_body.get("result", {}) if img_body else {}
    image_info = img_result.get("image_info") or []

    dyn_body = _find_api(apis, "detail_page_dynamic_info")
    dyn_result = dyn_body.get("result", {}) if dyn_body else {}
    dyn_price = dyn_result.get("price") or {}

    # ── SPU 섹션 파싱 ──────────────────────────────────────────────────────────
    sec_data = _extract_from_spu_sections(spu_sections)

    # ── 타이틀 ────────────────────────────────────────────────────────────────
    title = spu_basic.get("spu_name") or ""
    if not title and spu_groups:
        for g in spu_groups:
            spus = g.get("spu_list") or []
            if spus:
                title = spus[0].get("spu_name", "")
                break

    # ── 설명 (spu_desc) ───────────────────────────────────────────────────────
    description = ""
    if spu_groups:
        for g in spu_groups:
            for spu in g.get("spu_list") or []:
                if spu.get("spu_desc"):
                    description = spu["spu_desc"]
                    break
            if description:
                break

    # ── 가격 ─────────────────────────────────────────────────────────────────
    price_min = None
    price_currency = pkg_result.get("currency_symbol") or "₩"
    # packages에서 최저가 탐색
    for pkg in packages:
        sp = pkg.get("sell_price") or pkg.get("original_price")
        if sp is not None:
            try:
                sp = float(sp)
                if price_min is None or sp < price_min:
                    price_min = sp
            except (TypeError, ValueError):
                pass
    # activity_closer_price 폴백
    if price_min is None:
        sp = activity_closer_price.get("selling_price") or activity_closer_price.get("from_price")
        if sp is not None:
            try:
                price_min = float(sp)
            except (TypeError, ValueError):
                pass
    # dyn_price 폴백
    if price_min is None:
        sp = dyn_price.get("sale_price_value") or dyn_price.get("from_price_value")
        if sp is not None:
            try:
                price_min = float(sp)
            except (TypeError, ValueError):
                pass

    # ── 리뷰 통계 ─────────────────────────────────────────────────────────────
    review_star = None
    review_count = None
    if rev_result.get("score") is not None:
        review_star = float(rev_result["score"])
        review_count = str(rev_result.get("total") or "")
    elif rating_info.get("avg_rating") is not None:
        review_star = float(rating_info["avg_rating"])
        review_count = str(rating_info.get("review_count") or "")

    # ── 사진 URL ──────────────────────────────────────────────────────────────
    photos = [img.get("image_url") for img in image_info if img.get("image_url")]

    # ── 아이콘 뱃지 (확인 방식, 무료 취소 등) ────────────────────────────────
    badges = [it.get("title") for it in icon_items if it.get("title")]

    # ── 패키지 요약 ───────────────────────────────────────────────────────────
    pkg_summary = [
        {
            "id": p.get("package_id"),
            "name": p.get("package_name"),
            "price": p.get("sell_price"),
            "original_price": p.get("original_price"),
        }
        for p in packages
    ]

    # ── 리뷰 샘플 ─────────────────────────────────────────────────────────────
    review_samples = [
        {
            "author": rv.get("author"),
            "date": rv.get("date"),
            "rating": rv.get("rating"),
            "content": (rv.get("translate_content") or rv.get("content") or "")[:300],
            "package": rv.get("package_name"),
        }
        for rv in (reviews or ov_reviews)[:10]
    ]

    # ── FAQ ───────────────────────────────────────────────────────────────────
    faq_summary = []
    if isinstance(faqs, list):
        for f in faqs:
            if isinstance(f, dict):
                faq_summary.append({
                    "q": f.get("question") or f.get("q", ""),
                    "a": f.get("answer") or f.get("a", ""),
                })

    return {
        "activity_id": activity_id,
        "detail_url": url,
        "http_status": status,
        "title": title,
        "description": description,
        "highlights": _jstr(badges),
        "inclusions": _jstr(sec_data["inclusions"]),
        "exclusions": _jstr(sec_data["exclusions"]),
        "duration": None,
        "meeting_point": sec_data["meeting_point"] or None,
        "cancellation_policy": sec_data["cancellation_policy"] or None,
        "important_info": _jstr(sec_data["important_info"]),
        "photos_json": _jstr(photos),
        "faq_json": _jstr(faq_summary),
        "packages_json": _jstr(pkg_summary),
        "reviews_json": _jstr(review_samples),
        "price_min": str(int(price_min)) if price_min is not None else None,
        "price_currency": price_currency,
        "review_star": review_star,
        "review_count": review_count or None,
        "raw_apis_json": json.dumps(apis, ensure_ascii=False),
        "collected_at": now,
    }


# ── DB 저장 ───────────────────────────────────────────────────────────────────

def save_details(conn: sqlite3.Connection, rows: list[dict]) -> None:
    for row in rows:
        cols = list(row.keys())
        ph = ", ".join(["?"] * len(cols))
        conn.execute(
            f"INSERT OR REPLACE INTO product_details ({', '.join(cols)}) VALUES ({ph})",
            [row[c] for c in cols],
        )
    conn.commit()


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== Klook 상세페이지 수집 시작 ===\n")

    # 1) 상위 10개 상품
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        products = conn.execute(
            "SELECT activity_id, deep_link FROM products ORDER BY id LIMIT 10"
        ).fetchall()

    activities = [{"activity_id": r["activity_id"], "url": r["deep_link"]} for r in products]
    print(f"수집 대상 {len(activities)}개")

    # 2) 테이블/뷰 초기화
    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
    print("테이블/뷰 초기화 완료\n")

    # 3) Whale 실행
    print("Whale 브라우저 시작...")
    whale_proc = None
    try:
        whale_proc = launch_whale(WHALE_PORT)
        time.sleep(2)

        # 4) Node.js 스크래퍼
        print("\nNode.js 스크래퍼 실행...")
        raw_results = run_node_scraper(activities, WHALE_PORT)

        # 5) 파싱 & 저장
        detail_rows = []
        for item in raw_results:
            row = extract_detail(
                item["activity_id"],
                item.get("url", ""),
                item.get("status", "unknown"),
                item.get("apis", {}),
            )
            detail_rows.append(row)

        with sqlite3.connect(DB_PATH) as conn:
            save_details(conn, detail_rows)
        print(f"\n{len(detail_rows)}건 저장 완료")

    finally:
        if whale_proc:
            print("\nWhale 종료...")
            whale_proc.terminate()
            try:
                whale_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                whale_proc.kill()

    # 6) 결과 출력
    print("\n=== 수집 결과 ===")
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT activity_id, http_status, title, description, duration, "
            "highlights, faq_json, packages_json, photos_json FROM product_details ORDER BY id"
        ).fetchall()
        for r in rows:
            has = lambda f: "O" if r[f] and r[f] not in ("null", "[]", "{}") else "-"
            print(
                f"  [{r['http_status']:8s}] {r['activity_id']:6d} | {(r['title'] or '(없음)')[:35]:35s}"
                f" | 설명:{has('description')} 하이라이트:{has('highlights')}"
                f" FAQ:{has('faq_json')} 패키지:{has('packages_json')} 사진:{has('photos_json')}"
            )

    print("\n=== v_product_detail 조인 뷰 (상위 10개) ===")
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT activity_id, search_title, city, category,
                   http_status, duration, price_min, price_currency,
                   detail_review_star, detail_review_count
            FROM v_product_detail ORDER BY id LIMIT 10
        """).fetchall()
        print(f"  {'ID':6s} {'제목':35s} {'도시':8s} {'기간':12s} {'최저가':10s} {'별점':5s}")
        print("  " + "-" * 85)
        for r in rows:
            print(
                f"  {r['activity_id']:6d} {(r['search_title'] or '')[:35]:35s} "
                f"{(r['city'] or ''):8s} {(r['duration'] or '-'):12s} "
                f"{(r['price_min'] or '-'):10s} {str(r['detail_review_star'] or '-'):5s}"
            )

    print(f"\nDB 경로: {DB_PATH}")


if __name__ == "__main__":
    main()
