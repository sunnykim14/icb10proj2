"""
Klook 대한민국 검색 결과 1~10페이지 스크래핑 후 SQLite 저장.

Klook API는 인증 없이 쿼리당 최대 75건(5페이지)만 반환하므로,
도시/지역별 키워드 분산 수집 후 중복 제거하여 150건(10페이지) 이상 확보한다.
"""

import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import requests

BASE_URL = "https://www.klook.com/v1/cardinfocenterservicesrv/search/platform/complete_search_v3"

# 한국 주요 도시·지역 키워드 — 각 쿼리당 최대 75건, 중복 제거 후 합산
QUERIES = [
    "서울",
    "부산",
    "제주",
    "경기",
    "인천",
    "강원",
    "대구",
    "광주",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    ),
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "version": "5.6",
    "x-klook-host": "www.klook.com",
    "x-klook-market": "global",
    "x-klook-user-residence": "10_KR",
    "x-platform": "desktop",
    "x-requested-with": "XMLHttpRequest",
    "x-klook-channel-level-one": "SEM",
    "x-klook-traffic-channel": "google_sem",
}

PAGE_SIZE = 15
PAGES_PER_QUERY = 5   # 쿼리당 최대 수집 가능 페이지
TARGET_ROWS = 150     # 목표 저장 건수 (10페이지 × 15)

DB_PATH = Path(__file__).parent.parent / "data" / "klook.db"


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id     INTEGER UNIQUE,
            page_num        INTEGER NOT NULL,
            query_keyword   TEXT,
            title           TEXT,
            seo_title       TEXT,
            city            TEXT,
            category        TEXT,
            vertical_type   TEXT,
            selling_price   TEXT,
            market_price    TEXT,
            price_format    TEXT,
            review_star     REAL,
            review_count    TEXT,
            booked          TEXT,
            sold_out        INTEGER,
            tags            TEXT,
            cover_url       TEXT,
            deep_link       TEXT,
            collected_at    TEXT NOT NULL
        )
    """)
    conn.commit()


def extract_activity_id(deep_link: str | None) -> int | None:
    if not deep_link:
        return None
    m = re.search(r"/activity/(\d+)", deep_link)
    return int(m.group(1)) if m else None


def fetch_page(query: str, page: int) -> list[dict]:
    from urllib.parse import quote
    start = (page - 1) * PAGE_SIZE + 1
    params = {
        "sort": "most_relevant",
        "tab_key": "0",
        "start": str(start),
        "query": query,
        "size": str(PAGE_SIZE),
        "search_scope": "main_search",
        "k_lang": "ko_KR",
        "k_currency": "KRW",
    }
    encoded_query = quote(query, safe="")
    headers = {
        **HEADERS,
        "Referer": (
            f"https://www.klook.com/ko/search/result/?query={encoded_query}"
            f"&search_scope=main_search&sort=most_relevant&tab_key=0&start={start}"
        ),
    }
    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    body = resp.json()

    if not body.get("success"):
        raise RuntimeError(f"API 오류: {body.get('error')}")

    return body["result"]["search_result"]["cards"]


def extract_row(card: dict, page_num: int, query: str, collected_at: str) -> dict:
    data = card.get("data", {})
    price = data.get("price") or {}
    review = data.get("review_obj") or {}
    seo = data.get("seo") or {}
    tags = data.get("general_tag") or []
    tag_texts = " | ".join(t.get("text", "") for t in tags if t.get("text"))
    deep_link = data.get("deep_link")

    return {
        "activity_id": extract_activity_id(deep_link),
        "page_num": page_num,
        "query_keyword": query,
        "title": data.get("title"),
        "seo_title": seo.get("title"),
        "city": data.get("city_name"),
        "category": data.get("category"),
        "vertical_type": data.get("vertical_type"),
        "selling_price": str(price["selling_price"]) if price.get("selling_price") is not None else None,
        "market_price": str(price["market_price"]) if price.get("market_price") is not None else None,
        "price_format": price.get("selling_price_format"),
        "review_star": review.get("star"),
        "review_count": str(review["count"]) if review.get("count") is not None else None,
        "booked": str(review["booked"]) if review.get("booked") is not None else None,
        "sold_out": 1 if data.get("sold_out") else 0,
        "tags": tag_texts,
        "cover_url": data.get("cover_url"),
        "deep_link": deep_link,
        "collected_at": collected_at,
    }


def insert_row(conn: sqlite3.Connection, row: dict) -> bool:
    """중복(activity_id) 무시하고 삽입. 실제 삽입 여부 반환."""
    cols = list(row.keys())
    placeholders = ", ".join(["?"] * len(cols))
    sql = (
        f"INSERT OR IGNORE INTO products ({', '.join(cols)}) "
        f"VALUES ({placeholders})"
    )
    cur = conn.execute(sql, [row[c] for c in cols])
    return cur.rowcount == 1


def main() -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    print(f"DB 경로: {DB_PATH}\n")

    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)

        total_inserted = 0
        virtual_page = 1      # DB에 기록할 페이지 번호 (1~10)
        page_count = 0        # 현재 페이지 내 누적 건수
        done = False

        for query in QUERIES:
            if done:
                break

            print(f"\n[키워드: {query}]")
            for qpage in range(1, PAGES_PER_QUERY + 1):
                if done:
                    break
                try:
                    cards = fetch_page(query, qpage)
                    inserted_this = 0

                    for card in cards:
                        collected_at = datetime.now().isoformat(timespec="seconds")
                        row = extract_row(card, virtual_page, query, collected_at)
                        if insert_row(conn, row):
                            inserted_this += 1
                            total_inserted += 1
                            page_count += 1
                            if page_count >= PAGE_SIZE:
                                print(f"  → 페이지 {virtual_page:2d} 완료 ({PAGE_SIZE}건)")
                                virtual_page += 1
                                page_count = 0
                        if total_inserted >= TARGET_ROWS:
                            done = True
                            break

                    conn.commit()
                    print(f"  p{qpage}: {inserted_this}건 신규 삽입 (누적 {total_inserted}건)")

                    if not cards:
                        print(f"  → cards 없음, 다음 키워드로 이동")
                        break

                except Exception as e:
                    print(f"  p{qpage} 오류: {e}")

                if not done:
                    time.sleep(1.0)

    print(f"\n완료: 총 {total_inserted}건 저장 → {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT page_num, COUNT(*) AS cnt FROM products GROUP BY page_num ORDER BY page_num"
        ).fetchall()
        print("\n[페이지별 저장 건수]")
        for r in rows:
            print(f"  페이지 {r['page_num']:2d}: {r['cnt']}건")
        total_db = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        print(f"\n  DB 전체: {total_db}건")


if __name__ == "__main__":
    main()
