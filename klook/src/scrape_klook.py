"""
Klook 대한민국 검색 결과 스크래핑 스크립트.
API 엔드포인트에서 여행 상품 카드 데이터를 수집하여 CSV로 저장합니다.
"""

import json
import csv
import requests
from pathlib import Path

BASE_URL = "https://www.klook.com/v1/cardinfocenterservicesrv/search/platform/complete_search_v3"

PARAMS = {
    "location": "158,157,156,5031,8928,24975,28741,545,6166,6268,703649,703648,705582,6955,15088,701102,16467,707516,26374,7204,20296,28785,28972,8898,23546,30633,15378,16365,28742,10956,26961,10093,16560,25178,7741,11925,24865,25140,30570,7030,707332,7558,8989,10706,11364,11745,13523,14446,15281,15603,16655,18214,18323,20392,22390,22675,23237,24520,24762,25060,26454,27895,29136,29872,30051,30265,30376,30466,31247,705101,9079",
    "sort": "most_relevant",
    "tab_key": "0",
    "start": "1",
    "query": "대한민국",
    "size": "15",
    "search_scope": "main_search",
    "k_lang": "ko_KR",
    "k_currency": "KRW",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Whale/4.38.386.12 Safari/537.36",
    "Referer": "https://www.klook.com/ko/search/result/?query=%EB%8C%80%ED%95%9C%EB%AF%BC%EA%B5%AD&search_scope=main_search&sort=most_relevant&tab_key=0&start=1",
    "sec-ch-ua": '"Chromium";v="148", "Whale";v="4", "Not.A/Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "version": "5.6",
    "x-klook-channel-level-one": "SEM",
    "x-klook-host": "www.klook.com",
    "x-klook-market": "global",
    "x-klook-traffic-channel": "google_sem",
    "x-klook-user-residence": "10_KR",
    "x-platform": "desktop",
    "x-requested-with": "XMLHttpRequest",
}

OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)


def extract_card_fields(card: dict) -> dict:
    data = card.get("data", {})

    price = data.get("price") or {}
    review = data.get("review_obj") or {}
    seo = data.get("seo") or {}
    tags = data.get("general_tag") or []
    tag_texts = " | ".join(t.get("text", "") for t in tags if t.get("text"))

    return {
        "title": data.get("title"),
        "seo_title": seo.get("title"),
        "city": data.get("city_name"),
        "category": data.get("category"),
        "vertical_type": data.get("vertical_type"),
        "selling_price": price.get("selling_price"),
        "market_price": price.get("market_price"),
        "price_format": price.get("selling_price_format"),
        "review_star": review.get("star"),
        "review_count": review.get("count"),
        "booked": review.get("booked"),
        "sold_out": data.get("sold_out"),
        "tags": tag_texts,
        "cover_url": data.get("cover_url"),
        "deep_link": data.get("deep_link"),
    }


def fetch_page() -> list[dict]:
    resp = requests.get(BASE_URL, params=PARAMS, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    body = resp.json()

    if not body.get("success"):
        raise RuntimeError(f"API 오류: {body.get('error')}")

    cards = body["result"]["search_result"]["cards"]
    total = body["result"]["search_result"]["total"]
    print(f"전체 상품 수: {total}, 이번 페이지 수집 건수: {len(cards)}")

    # 첫 번째 카드 구조 출력 (필드 파악용)
    if cards:
        print("\n[첫 번째 카드 data 키 목록]")
        print(json.dumps(list(cards[0].get("data", {}).keys()), ensure_ascii=False, indent=2))

    return cards


def save_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        print("저장할 데이터가 없습니다.")
        return

    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nCSV 저장 완료: {path} ({len(rows)}건)")


def main():
    print("=== Klook 대한민국 검색 결과 수집 시작 ===\n")
    cards = fetch_page()
    rows = [extract_card_fields(c) for c in cards]
    output_path = OUTPUT_DIR / "klook_korea_page1.csv"
    save_csv(rows, output_path)


if __name__ == "__main__":
    main()
