"""
yes24 베스트셀러 도서 정보를 수집하여 CSV 파일로 저장하는 크롤러 스크립트입니다.
"""
import os
import csv
import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_yes24_bestsellers():
    url = "https://www.yes24.com/product/category/BestSellerContents?categoryNumber=001001003&sumGb=06&sex=A&age=255&goodsTp=0&addOptionTp=0&excludeTp=2&pageNumber=1&pageSize=24&goodsStatGb=06&eBookTp=0&bestType=YES24_BESTSELLER&type=&saleYear=0&saleMonth=0&weekNo=0&saleDts=&viewMode=&freeYn="
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.yes24.com/"
    }
    
    print("yes24 베스트셀러 페이지 요청 중...")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"오류 발생: HTTP {response.status_code}")
        return
    
    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.find_all("div", class_="itemUnit")
    
    print(f"발견된 도서 수: {len(items)}")
    
    data_list = []
    
    for item in items:
        # 1. 순위
        rank_elem = item.find("em", class_="ico rank")
        rank = rank_elem.get_text(strip=True) if rank_elem else ""
        
        # 2. 도서명
        name_elem = item.find("a", class_="gd_name")
        book_name = name_elem.get_text(strip=True) if name_elem else ""
        
        # 3. 부제목
        subtitle_elem = item.find("span", class_="gd_nameE")
        subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else ""
        
        # 4. 특징
        features = []
        feature_grp = item.find("span", class_="gd_feature")
        if feature_grp:
            feature_elems = feature_grp.find_all("span", class_="feature")
            features = [f.get_text(strip=True) for f in feature_elems]
        features_str = ", ".join(features)
        
        # 5. 저자
        author_elem = item.find("span", class_="info_auth")
        author = ""
        if author_elem:
            author_a = author_elem.find("a")
            if author_a:
                author = author_a.get_text(strip=True)
            else:
                author = author_elem.get_text(strip=True).replace(" 저", "")
                
        # 6. 출판사
        pub_elem = item.find("span", class_="info_pub")
        publisher = ""
        if pub_elem:
            pub_a = pub_elem.find("a")
            publisher = pub_a.get_text(strip=True) if pub_a else pub_elem.get_text(strip=True)
            
        # 7. 출간일
        date_elem = item.find("span", class_="info_date")
        publish_date = date_elem.get_text(strip=True) if date_elem else ""
        
        # 8. 구매혜택
        benefit_elem = item.find("dl", class_="info_present")
        benefit = ""
        if benefit_elem:
            benefit_dd = benefit_elem.find("dd")
            if benefit_dd:
                benefit_a = benefit_dd.find("a")
                benefit = benefit_a.get_text(strip=True) if benefit_a else benefit_dd.get_text(strip=True)
                
        # 9. 판매가 및 할인율, 원가
        price_elem = item.find("div", class_="info_price")
        discount_rate = ""
        sale_price = ""
        original_price = ""
        ypoint = ""
        if price_elem:
            disc_rate_elem = price_elem.find("span", class_="txt_sale")
            if disc_rate_elem:
                discount_rate = disc_rate_elem.get_text(strip=True)
            
            sale_price_elem = price_elem.find("strong", class_="txt_num")
            if sale_price_elem:
                sale_price = sale_price_elem.find("em", class_="yes_b").get_text(strip=True) if sale_price_elem.find("em", class_="yes_b") else sale_price_elem.get_text(strip=True)
            
            orig_price_elem = price_elem.find("span", class_="txt_num dash")
            if orig_price_elem:
                original_price = orig_price_elem.find("em", class_="yes_m").get_text(strip=True) if orig_price_elem.find("em", class_="yes_m") else orig_price_elem.get_text(strip=True)
                
            ypoint_elem = price_elem.find("span", class_="yPoint")
            if ypoint_elem:
                ypoint = ypoint_elem.get_text(strip=True).replace("포인트적립", "")
                
        # 10. 판매지수 및 평점/리뷰
        sales_index = ""
        review_count = ""
        rating = ""
        rating_elem = item.find("div", class_="info_rating")
        if rating_elem:
            salenum_elem = rating_elem.find("span", class_="saleNum")
            if salenum_elem:
                sales_index = salenum_elem.get_text(strip=True).replace("판매지수", "").strip()
                
            rv_elem = rating_elem.find("span", class_="rating_rvCount")
            if rv_elem:
                rv_count_em = rv_elem.find("em", class_="txC_blue")
                review_count = rv_count_em.get_text(strip=True) if rv_count_em else rv_elem.get_text(strip=True)
                
            grade_elem = rating_elem.find("span", class_="rating_grade")
            if grade_elem:
                grade_em = grade_elem.find("em", class_="yes_b")
                rating = grade_em.get_text(strip=True) if grade_em else ""
                
        # 11. 배송 정보
        deli_elem = item.find("div", class_="info_deli")
        delivery_info = ""
        if deli_elem:
            deli_des = deli_elem.find("span", class_="deli_des")
            deli_date = deli_elem.find("span", class_="deli_date")
            des_str = deli_des.get_text(strip=True) if deli_des else ""
            date_str = deli_date.get_text(strip=True) if deli_date else ""
            delivery_info = f"{des_str} {date_str}".strip()
            
        # 12. 태그
        tag_elem = item.find("div", class_="info_tag")
        tags = []
        if tag_elem:
            tag_spans = tag_elem.find_all("span", class_="tag")
            tags = [t.get_text(strip=True) for t in tag_spans]
        tags_str = ", ".join(tags)
        
        data_list.append({
            "순위": rank,
            "도서명": book_name,
            "부제목": subtitle,
            "특징": features_str,
            "저자": author,
            "출판사": publisher,
            "출간일": publish_date,
            "구매혜택": benefit,
            "할인율": discount_rate,
            "판매가": sale_price,
            "정가": original_price,
            "적립포인트": ypoint,
            "판매지수": sales_index,
            "리뷰수": review_count,
            "평점": rating,
            "배송정보": delivery_info,
            "태그": tags_str
        })
        
    df = pd.DataFrame(data_list)
    os.makedirs("yes24/data", exist_ok=True)
    csv_path = "yes24/data/best_sellers.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"데이터 수집 완료! 저장 경로: {csv_path}")
    
if __name__ == "__main__":
    scrape_yes24_bestsellers()
