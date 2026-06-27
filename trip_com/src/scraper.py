"""
Trip.com 호텔 리뷰 스크래퍼
- curl_cffi (scrapling 핵심 의존성)로 실제 Chrome TLS 핑거프린트 위장
- POST API 호출 → JSON 파싱 → SQLite 저장
- 대상: 호텔 ID 58635410 (서울)
"""
import json
import sqlite3
import time
import os
import sys
import io

# Windows 콘솔 UTF-8 출력
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests as cf_req

API_URL = "https://kr.trip.com/restapi/soa2/34308/getHotelCommentInfo"
HOTEL_ID = 58635410
PAGE_SIZE = 10
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "reviews.db")

HEADERS = {
    "accept": "*/*",
    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "content-type": "application/json",
    "origin": "https://kr.trip.com",
    "referer": "https://kr.trip.com/hotels/detail/?cityEnName=Seoul&cityId=274&hotelId=58635410",
    "sec-ch-ua": '"Google Chrome";v="131"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "w-payload-source": (
        "1.0.9@102!Nudtz1KLhCAbOX4SO6An9PKnG2KLOSqZOlbn+6FaG6OaKSbpKET2OSVbOrK2"
        "+ET5+rApbbbpOSknKr42+rG2KlqIbEVbKtb5+rbSOEb2KE4p+rKpOr4nKrq/K5bpOSqL"
        "+rk/OSKZKrVpQlVROShDKFO3GVd3hbb="
    ),
    "x-ctx-country": "KR",
    "x-ctx-currency": "KRW",
    "x-ctx-locale": "ko-KR",
    "x-ctx-ubt-pageid": "10320668147",
    "x-ctx-ubt-pvid": "7",
    "x-ctx-ubt-sid": "9",
    "x-ctx-ubt-vid": "1754985737191.9877n1SlbHlt",
    "x-ctx-user-recognize": "NON_EU",
    "x-ctx-wclient-req": "0af33fe7acb74bcfe9f82cf404544b46",
}


def build_payload(page_index: int) -> dict:
    return {
        "hotelId": HOTEL_ID,
        "commentFilterOptions": {
            "pageIndex": page_index,
            "pageSize": PAGE_SIZE,
            "repeatComment": 1,
        },
        "sceneTypes": ["CommentList"],
        "head": {
            "platform": "PC",
            "cver": "0",
            "cid": "1754985737191.9877n1SlbHlt",
            "bu": "IBU",
            "group": "trip",
            "aid": "",
            "sid": "",
            "ouid": "",
            "locale": "ko-KR",
            "timezone": "9",
            "currency": "KRW",
            "pageId": "10320668147",
            "vid": "1754985737191.9877n1SlbHlt",
            "guid": "",
            "isSSR": False,
        },
    }


def fetch_page(session: cf_req.Session, page_index: int) -> dict | None:
    payload = build_payload(page_index)
    resp = session.post(
        API_URL,
        json=payload,
        headers=HEADERS,
        impersonate="chrome131",
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  [오류] HTTP {resp.status_code}")
        return None
    return resp.json()


def parse_reviews(data: dict) -> list[dict]:
    """응답 JSON에서 리뷰 목록 추출."""
    reviews = []
    try:
        inner = data.get("data", {})
        group_list = inner.get("groupList", [])
        if not group_list:
            return reviews
        comment_list = group_list[0].get("commentList", [])
        for item in comment_list:
            ui = item.get("userInfo", {})
            ri = item.get("ratingInfo", {})

            # 호텔 답변 (feedbackList 첫 번째 항목)
            fb_list = item.get("feedbackList", [])
            hotel_reply = ""
            hotel_reply_date = ""
            if fb_list:
                hotel_reply = fb_list[0].get("content", "")
                hotel_reply_date = fb_list[0].get("createDate", "")

            # 리뷰 이미지 URL 목록 (JSON 직렬화)
            images = item.get("imageCuttingsList", [])
            image_urls = json.dumps(
                [img.get("mediumImageUrl", "") for img in images if img.get("mediumImageUrl")],
                ensure_ascii=False,
            )
            image_count = len(images)

            review = {
                "review_id":        str(item.get("id", "")),
                "user_name":        ui.get("nickName", ""),
                "user_region":      ui.get("regionName", ""),
                "user_region_code": ui.get("regionCode", ""),
                "rating":           item.get("rating", None),
                "rating_label":     ri.get("commentLevel", ""),
                "rating_location":  ri.get("ratingLocation", None),
                "rating_facility":  ri.get("ratingFacility", None),
                "rating_service":   ri.get("ratingService", None),
                "rating_room":      ri.get("ratingRoom", None),
                "content":          item.get("content", ""),
                "content_ko":       item.get("translatedContent", ""),
                "language":         item.get("language", ""),
                "trip_type":        item.get("travelTypeText", ""),
                "stay_date":        item.get("checkinDate", ""),
                "created_at":       item.get("createDate", ""),
                "helpful_count":    item.get("usefulCount", 0),   # 리뷰 레벨 usefulCount
                "recommend":        1 if item.get("recommend") else 0,
                "room_name":        item.get("roomName", ""),
                "room_id":          item.get("roomID", None),
                "hotel_reply":      hotel_reply,
                "hotel_reply_date": hotel_reply_date,
                "image_urls":       image_urls,
                "image_count":      image_count,
            }
            reviews.append(review)
    except (KeyError, TypeError, IndexError) as e:
        print(f"  [파싱 오류] {e}")
    return reviews


def get_total_pages(data: dict) -> tuple[int, int]:
    """(총 리뷰 수, 총 페이지 수) 반환."""
    try:
        total_count = int(data.get("data", {}).get("totalCountForPage", 0))
        pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
        return total_count, pages
    except (ValueError, TypeError):
        return 0, 1


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            review_id        TEXT PRIMARY KEY,
            hotel_id         INTEGER,
            user_name        TEXT,
            user_region      TEXT,
            user_region_code TEXT,
            rating           REAL,
            rating_label     TEXT,
            rating_location  REAL,
            rating_facility  REAL,
            rating_service   REAL,
            rating_room      REAL,
            content          TEXT,
            content_ko       TEXT,
            language         TEXT,
            trip_type        TEXT,
            stay_date        TEXT,
            created_at       TEXT,
            helpful_count    INTEGER,
            recommend        INTEGER,
            room_name        TEXT,
            room_id          INTEGER,
            hotel_reply      TEXT,
            hotel_reply_date TEXT,
            image_urls       TEXT,
            image_count      INTEGER
        )
    """)
    # 기존 테이블에 신규 컬럼 추가 (이미 있으면 무시)
    new_cols = [
        ("recommend",        "INTEGER"),
        ("room_name",        "TEXT"),
        ("room_id",          "INTEGER"),
        ("hotel_reply",      "TEXT"),
        ("hotel_reply_date", "TEXT"),
        ("image_urls",       "TEXT"),
        ("image_count",      "INTEGER"),
    ]
    existing = {row[1] for row in conn.execute("PRAGMA table_info(reviews)")}
    for col, col_type in new_cols:
        if col not in existing:
            conn.execute(f"ALTER TABLE reviews ADD COLUMN {col} {col_type}")
    conn.commit()


def save_reviews(conn: sqlite3.Connection, reviews: list[dict]) -> int:
    updated = 0
    for r in reviews:
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO reviews
                  (review_id, hotel_id, user_name, user_region, user_region_code,
                   rating, rating_label, rating_location, rating_facility,
                   rating_service, rating_room,
                   content, content_ko, language, trip_type,
                   stay_date, created_at, helpful_count,
                   recommend, room_name, room_id,
                   hotel_reply, hotel_reply_date,
                   image_urls, image_count)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    r["review_id"], HOTEL_ID,
                    r["user_name"], r["user_region"], r["user_region_code"],
                    r["rating"], r["rating_label"],
                    r["rating_location"], r["rating_facility"],
                    r["rating_service"], r["rating_room"],
                    r["content"], r["content_ko"], r["language"],
                    r["trip_type"], r["stay_date"],
                    r["created_at"], r["helpful_count"],
                    r["recommend"], r["room_name"], r["room_id"],
                    r["hotel_reply"], r["hotel_reply_date"],
                    r["image_urls"], r["image_count"],
                ),
            )
            updated += 1
        except sqlite3.Error as e:
            print(f"  [DB 오류] {e}")
    conn.commit()
    return updated


def verify_first_page(reviews: list[dict]) -> bool:
    """첫 페이지 수집 검증: 내용(content) + 별점(rating) 필수."""
    if not reviews:
        print("  [검증 실패] 리뷰가 없습니다.")
        return False

    sample = reviews[0]
    print(f"  --- 첫 번째 리뷰 샘플 ---")
    print(f"  작성자   : {sample['user_name']} ({sample['user_region']})")
    print(f"  별점     : {sample['rating']} / 10  ({sample['rating_label']})")
    print(f"  원문언어 : {sample['language']}")
    print(f"  내용(원문): {sample['content'][:80]!r}")
    print(f"  내용(번역): {sample['content_ko'][:80]!r}")
    print(f"  여행유형 : {sample['trip_type']}")
    print(f"  객실명   : {sample['room_name']}")
    print(f"  추천여부 : {'예' if sample['recommend'] else '아니오'}")
    print(f"  이미지수 : {sample['image_count']}장")
    print(f"  호텔답변 : {sample['hotel_reply'][:60]!r}" if sample['hotel_reply'] else "  호텔답변 : 없음")
    print(f"  체크인   : {sample['stay_date']}")
    print(f"  작성일   : {sample['created_at']}")
    print(f"  -------------------------")

    if sample["rating"] is None:
        print("  [검증 실패] 별점 없음")
        return False
    if not sample["content"] and not sample["content_ko"]:
        print("  [검증 실패] 내용 없음")
        return False

    print("  [검증 통과] 별점 / 내용 모두 정상 수집됨")
    return True


def main() -> None:
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    session = cf_req.Session()

    # ── 1단계: 첫 페이지 수집 및 검증 ──────────────────────────────────
    print("=" * 55)
    print("[1단계] 첫 페이지 수집 중 (pageIndex=1)...")
    data = fetch_page(session, page_index=1)
    if data is None:
        print("첫 페이지 수집 실패. 종료합니다.")
        conn.close()
        return

    reviews_p1 = parse_reviews(data)
    total_count, total_pages = get_total_pages(data)
    print(f"  수집된 리뷰: {len(reviews_p1)}개  |  전체: {total_count}개 ({total_pages} 페이지)")

    if not verify_first_page(reviews_p1):
        print("첫 페이지 검증 실패. 전체 수집을 중단합니다.")
        conn.close()
        return

    saved = save_reviews(conn, reviews_p1)
    print(f"  DB 저장: {saved}개 (신규)")

    if total_pages <= 1:
        print("리뷰가 1페이지뿐입니다.")
        conn.close()
        return

    # ── 2단계: 전체 페이지 수집 ────────────────────────────────────────
    print()
    print(f"[2단계] 나머지 {total_pages - 1} 페이지 수집 시작...")
    total_saved = saved

    for page_idx in range(2, total_pages + 1):
        print(f"  페이지 {page_idx:>3}/{total_pages} ...", end=" ", flush=True)
        data = fetch_page(session, page_index=page_idx)
        if data is None:
            print("실패, 건너뜀")
            continue
        reviews = parse_reviews(data)
        n = save_reviews(conn, reviews)
        total_saved += n
        print(f"{len(reviews)}개 수집, {n}개 저장")
        time.sleep(0.8)

    conn.close()
    print()
    print("=" * 55)
    print(f"완료! 총 {total_saved}개 리뷰 저장")
    print(f"DB 경로: {os.path.abspath(DB_PATH)}")


if __name__ == "__main__":
    main()
