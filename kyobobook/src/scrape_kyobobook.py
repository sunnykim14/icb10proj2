# kyobobook/src/scrape_kyobobook.py
"""
Kyobo Bookstore 베스트셀러 API 스크래핑 스크립트

- API 엔드포인트와 헤더는 scraping_prompt.md 에 정의된 내용을 참고합니다.
- 페이지당 50개씩 데이터를 가져와서 `kyobobook/data/best_sellers.csv` 로 저장합니다.
- 이미 존재하는 CSV 파일이 있으면 헤더를 제외하고 데이터를 추가합니다.
- 스크립트는 상대 경로(`../data`) 를 사용하므로 워크스페이스 루트에서 실행해야 합니다.

사용법:
    python -m src.scrape_kyobobook   # 워크스페이스 루트에서 실행
"""

import json
import csv
import os
from pathlib import Path
import requests

# ---------------------------------------------------------------------------
# 설정 (scraping_prompt.md 에서 복사)
# ---------------------------------------------------------------------------
BASE_URL = "https://store.kyobobook.co.kr/api/gw/best/v2/best-seller/online"
HEADERS = {
    "host": "store.kyobobook.co.kr",
    "referer": "https://store.kyobobook.co.kr/category/domestic/33/best?page=1&per=50",
    "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-ch-ua-platform-version": "\"26.5.1\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "x-api-gw-key": "eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..i35xkkCOngvXqCRx.0CqToQel6sj5d0qOS2ftoDu37jRwb0vtQwMBd1e_G1ynl7KUrTrH_qPJnygVpkc0tExt4BUX_pJ4RepB5QsxWmKLjC8tEuMELKG8SvRLEVn6ambMnSmDaJ85mLbGtHcM-zFiDBzi.3y1-RnxGHFxeLNMK2dWZoQ"
}

# ---------------------------------------------------------------------------
# CSV 저장 설정
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CSV_PATH = DATA_DIR / "best_sellers.csv"

# ---------------------------------------------------------------------------
# 유틸리티 함수
# ---------------------------------------------------------------------------
def fetch_page(page: int = 1, per: int = 50) -> dict:
    """단일 페이지를 조회하고 JSON 응답을 반환합니다."""
    params = {
        "page": page,
        "per": per,
        "saleCmdtClstCode": "33",
        "soldOutExcludeYn": "N",
        "saleCmdtDsplDvsnCode": "KOR",
        "period": "002",
        "dsplDvsnCode": "001",
        "dsplTrgtDvsnCode": "004",
    }
    response = requests.get(BASE_URL, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

def parse_items(json_data: dict) -> list[dict]:
    """JSON 구조에서 필요한 필드만 추출합니다."""
    items = []
    for entry in json_data.get("data", {}).get("bestSeller", []):
        product = entry.get("product", {})
        info = product.get("productInfo", {})
        price = product.get("priceInfo", {})
        sale_cmdtid = info.get("saleCmdtid", "")
        items.append({
            "rank": entry.get("prstRnkn"),
            "title": info.get("cmdtName"),
            "author": info.get("chrcName"),
            "publisher": info.get("pbcmName"),
            "isbn": info.get("isbn"),
            "category": info.get("cmdtClstName"),
            "release_date": info.get("rlseDate"),
            "sale_price": price.get("saleCmdtSapr"),
            "price": price.get("saleCmdtPrce"),
            "discount": price.get("saleCmdtPrceDscnRate"),
            "url": f"https://product.kyobobook.co.kr/detail/{sale_cmdtid}" if sale_cmdtid else None,
        })
    return items

def save_to_csv(rows: list[dict]):
    """CSV 파일에 데이터를 저장합니다. 기존 파일이 있을 경우 헤더는 한 번만 씁니다."""
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = CSV_PATH.is_file()
    with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["rank", "title", "author", "publisher", "isbn", "category", "release_date", "sale_price", "price", "discount", "url"])
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)

def main():
    page = 1
    while True:
        data = fetch_page(page=page)
        items = parse_items(data)
        if not items:
            break
        save_to_csv(items)
        print(f"Page {page} - {len(items)} items saved.")
        page += 1

if __name__ == "__main__":
    main()
