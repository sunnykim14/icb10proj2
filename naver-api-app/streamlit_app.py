"""
네이버 검색 API를 활용한 Streamlit 대시보드 애플리케이션
Naver API를 활용한 검색 및 데이터 시각화 고도화 버전

주요 개선 기능:
- API 캐싱 기능 추가 (st.cache_data를 이용한 1시간 캐싱 적용)
- 분석 실행 제어 도입 (사이드바의 "분석 실행" 버튼 클릭 시에만 API 호출)
- 캐시 강제 새로고침 기능 지원 ("캐시 초기화" 버튼)
- 로컬 환경 (.env 파일) 및 배포 환경 (st.secrets) API 키 우선순위 바인딩
- 수동 API 키 입력 지원 및 마스킹(type="password") 보안 강화
- 검색 도메인별 데이터 획득 함수 모듈화 (순수 검색 인자 기반 캐싱 최적화)
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re
import os
from dotenv import load_dotenv

# 로컬 개발 환경용 .env 파일 로드
load_dotenv()

# API 키 조회 함수 (1순위: 환경변수/.env, 2순위: Streamlit Secrets)
def get_naver_api_key(key_name: str) -> str:
    # 1. 환경 변수 및 .env에서 조회
    val = os.getenv(key_name)
    if val:
        return val
    # 2. Streamlit Secrets에서 조회
    try:
        if key_name in st.secrets:
            return st.secrets[key_name]
    except Exception:
        pass
    return ""

# ---------- API 키 로드 및 설정 ----------
default_client_id = get_naver_api_key("NAVER_CLIENT_ID")
default_client_secret = get_naver_api_key("NAVER_CLIENT_SECRET")

# ---------- 사이드바 입력 ----------
st.sidebar.title("Naver API 설정")
client_id = st.sidebar.text_input(
    "Client ID", 
    value=default_client_id, 
    type="password" if default_client_id else "default"
)
client_secret = st.sidebar.text_input(
    "Client Secret", 
    value=default_client_secret, 
    type="password" if default_client_secret else "default"
)

st.sidebar.title("검색 옵션")
keywords_raw = st.sidebar.text_input("검색어 (콤마 구분)", "파이썬, 인공지능")
# 날짜 입력 (디폴트: 오늘 - 7일 ~ 오늘)
end_date = st.sidebar.date_input("종료 날짜", datetime.today())
start_date = st.sidebar.date_input("시작 날짜", datetime.today() - timedelta(days=7))

# 페이지 선택
page = st.sidebar.selectbox(
    "대시보드 페이지",
    ["검색어 트렌드", "쇼핑", "블로그", "카페", "뉴스", "쇼핑 트렌드"],
)

# ---------- 헬퍼 함수 ----------
def _headers():
    return {
        "X-Naver-Client-Id": client_id.strip(),
        "X-Naver-Client-Secret": client_secret.strip(),
    }

def _parse_keywords(raw: str):
    return tuple([kw.strip() for kw in raw.split(",") if kw.strip()])

def clean_html(text):
    if not isinstance(text, str):
        return text
    return re.sub(r'<[^>]*>', '', text)

# ---------- 캐싱 처리된 API 호출 모듈화 함수들 ----------
# API 요청 실패 시 캐시가 오염되는 것을 막기 위해 st.error를 출력하는 대신 raise_for_status()로 예외를 발생시키고 상위에서 핸들링합니다.

@st.cache_data(ttl=3600)
def fetch_keyword_trend(keywords_tuple: tuple, start_date, end_date):
    url = "https://openapi.naver.com/v1/datalab/search"
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    body = {
        "startDate": start_str,
        "endDate": end_str,
        "timeUnit": "date",
        "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in keywords_tuple],
        "device": "pc",
    }
    resp = requests.post(url, headers=_headers(), json=body, timeout=10)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=3600)
def fetch_shopping_data(keywords_tuple: tuple):
    base_url = "https://openapi.naver.com/v1/search/shop"
    all_items = []
    for kw in keywords_tuple:
        params = {"query": kw, "display": 30, "start": 1, "sort": "sim"}
        resp = requests.get(base_url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            for item in data.get("items", []):
                item['search_keyword'] = kw
                all_items.append(item)
    return all_items

@st.cache_data(ttl=3600)
def fetch_blog_data(keywords_tuple: tuple):
    base_url = "https://openapi.naver.com/v1/search/blog"
    all_blogs = []
    for kw in keywords_tuple:
        params = {"query": kw, "display": 30, "start": 1, "sort": "sim"}
        resp = requests.get(base_url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            for item in data.get("items", []):
                item['search_keyword'] = kw
                all_blogs.append(item)
    return all_blogs

@st.cache_data(ttl=3600)
def fetch_cafe_data(keywords_tuple: tuple):
    base_url = "https://openapi.naver.com/v1/search/cafearticle"
    all_cafes = []
    for kw in keywords_tuple:
        params = {"query": kw, "display": 30, "start": 1, "sort": "sim"}
        resp = requests.get(base_url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            for item in data.get("items", []):
                item['search_keyword'] = kw
                all_cafes.append(item)
    return all_cafes

@st.cache_data(ttl=3600)
def fetch_news_data(keywords_tuple: tuple):
    base_url = "https://openapi.naver.com/v1/search/news"
    all_news = []
    for kw in keywords_tuple:
        params = {"query": kw, "display": 50, "start": 1, "sort": "sim"}
        resp = requests.get(base_url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            for item in data.get("items", []):
                item['search_keyword'] = kw
                all_news.append(item)
    return all_news


# ---------- API 호출 버튼 제어 및 세션 관리 ----------
st.sidebar.markdown("---")
st.sidebar.subheader("데이터 업데이트")

# 세션 상태 변수 초기화
if "run_analysis" not in st.session_state:
    st.session_state.run_analysis = False
if "last_keywords" not in st.session_state:
    st.session_state.last_keywords = None
if "last_start_date" not in st.session_state:
    st.session_state.last_start_date = None
if "last_end_date" not in st.session_state:
    st.session_state.last_end_date = None

keywords = _parse_keywords(keywords_raw)

# 버튼 두 개 배치 (분석 실행 및 캐시 초기화)
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🔍 분석 실행", use_container_width=True):
        if not client_id or not client_secret:
            st.sidebar.error("API 키를 먼저 입력해주세요.")
        elif not keywords:
            st.sidebar.error("검색어를 입력해주세요.")
        else:
            st.session_state.run_analysis = True
            st.session_state.last_keywords = keywords
            st.session_state.last_start_date = start_date
            st.session_state.last_end_date = end_date
with col2:
    if st.button("🔄 캐시 초기화", use_container_width=True):
        st.cache_data.clear()
        st.sidebar.success("캐시 초기화 완료!")
        st.rerun()


# ---------- 메인 분석 로직 ----------
if not client_id or not client_secret:
    st.warning("API 키(Client ID, Client Secret)를 입력해주세요.")
    st.info("💡 사이드바에서 수동으로 입력하거나 로컬 환경의 `.env` 또는 배포 설정에 등록할 수 있습니다.")
    st.stop()

if not keywords:
    st.warning("검색어를 입력해주세요.")
    st.stop()

# 사용자가 아직 한 번도 분석 버튼을 누르지 않은 상태일 경우 안내
if not st.session_state.run_analysis:
    st.info("👈 왼쪽 사이드바에서 검색 옵션을 설정한 뒤 **[🔍 분석 실행]** 버튼을 눌러 시각화 분석을 기동하세요.")
    st.stop()

# 실행에 사용할 검색 옵션 바인딩
run_kws = st.session_state.last_keywords
run_start = st.session_state.last_start_date
run_end = st.session_state.last_end_date

# 각 페이지 렌더링 시작
if page == "검색어 트렌드":
    st.header("📈 네이버 검색어 트렌드 (데이터랩)")
    st.markdown("입력한 검색어들의 네이버 검색 트렌드를 비교 분석합니다. 가장 검색량이 높았던 시점을 100으로 설정한 상대값입니다.")
    
    with st.spinner("네이버 데이터랩 트렌드를 분석 중..."):
        try:
            data = fetch_keyword_trend(run_kws, run_start, run_end)
        except Exception as e:
            st.error(f"데이터 수집에 실패했습니다. (API 설정 및 네트워크 상태 확인 필요): {e}")
            data = None
            
    if data:
        all_data = []
        for grp in data.get("results", []):
            title = grp.get('title', grp.get('groupName'))
            for item in grp.get("data", []):
                all_data.append({
                    "period": item.get("period"),
                    "ratio": item.get("ratio"),
                    "keyword": title
                })
        
        if all_data:
            df = pd.DataFrame(all_data)
            df["period"] = pd.to_datetime(df["period"]).dt.date
            
            # Plotly Line Chart
            fig = px.line(
                df, x="period", y="ratio", color="keyword",
                title="일자별 검색어 트렌드 추이",
                labels={"period": "날짜", "ratio": "검색량 비율", "keyword": "검색어"},
                markers=True
            )
            fig.update_layout(hovermode="x unified", legend_title_text="키워드")
            st.plotly_chart(fig, use_container_width=True)
            
            # Pivot table
            df_pivot = df.pivot(index="period", columns="keyword", values="ratio").reset_index()
            st.subheader("📋 상세 트렌드 수치")
            st.dataframe(df_pivot.set_index("period"), use_container_width=True)
        else:
            st.warning("조회된 트렌드 데이터가 없습니다.")

elif page == "쇼핑":
    st.header("🛍️ 네이버 쇼핑 검색 및 가격 분석")
    
    with st.spinner("쇼핑 데이터를 수집하고 분석하는 중..."):
        try:
            all_items = fetch_shopping_data(run_kws)
        except Exception as e:
            st.error(f"쇼핑 데이터 수집 실패: {e}")
            all_items = []
                    
    if all_items:
        df = pd.DataFrame(all_items)
        df['title'] = df['title'].apply(clean_html)
        
        if 'lprice' in df.columns:
            df['price'] = pd.to_numeric(df['lprice'], errors='coerce')
            
            # KPI Cards
            st.subheader("💡 쇼핑 데이터 요약")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="최고가", value=f"{int(df['price'].max()):,}원")
            with col2:
                st.metric(label="최저가", value=f"{int(df['price'].min()):,}원")
            with col3:
                st.metric(label="평균가", value=f"{int(df['price'].mean()):,}원")
            
            # Plotly Bar Chart
            st.subheader("📊 상품별 가격 비교 (상위 10개)")
            df_top = df.sort_values(by="price", ascending=False).head(10)
            fig = px.bar(
                df_top, x="price", y="title", color="search_keyword",
                orientation="h",
                title="가장 높은 가격으로 등록된 상품 Top 10",
                labels={"price": "가격 (원)", "title": "상품명", "search_keyword": "키워드"},
                hover_data=["mallName"]
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
            
            # Mall distribution pie chart
            st.subheader("🛒 주요 판매몰(Mall) 분포")
            df_mall = df['mallName'].value_counts().reset_index()
            df_mall.columns = ['mallName', 'count']
            fig_mall = px.pie(
                df_mall, values='count', names='mallName',
                title='상품이 가장 많이 등록된 쇼핑몰 분포'
            )
            st.plotly_chart(fig_mall, use_container_width=True)
            
            # Display table
            st.subheader("📋 전체 쇼핑 상품 리스트")
            st.dataframe(
                df[['title', 'price', 'mallName', 'brand', 'search_keyword']],
                use_container_width=True
            )
        else:
            st.warning("가격 데이터가 존재하지 않습니다.")
    else:
        st.warning("조회된 쇼핑 데이터가 없습니다.")

elif page == "블로그":
    st.header("📝 네이버 블로그 검색 및 포스팅 분석")
    
    with st.spinner("블로그 포스팅 수집 중..."):
        try:
            all_blogs = fetch_blog_data(run_kws)
        except Exception as e:
            st.error(f"블로그 데이터 수집 실패: {e}")
            all_blogs = []
                    
    if all_blogs:
        df = pd.DataFrame(all_blogs)
        df['title'] = df['title'].apply(clean_html)
        df['description'] = df['description'].apply(clean_html)
        
        # Analyze top bloggers
        st.subheader("📊 주요 블로거 분포 (Top 10)")
        df_blogger = df['bloggername'].value_counts().reset_index().head(10)
        df_blogger.columns = ['bloggername', 'count']
        fig = px.bar(
            df_blogger, x='count', y='bloggername', orientation='h',
            title='상위 블로그 포스터 분석',
            labels={'count': '포스트 개수', 'bloggername': '블로그명'}
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Display table
        st.subheader("📋 블로그 검색 리스트")
        st.dataframe(
            df[['title', 'description', 'bloggername', 'postdate', 'search_keyword']],
            use_container_width=True
        )
    else:
        st.warning("조회된 블로그 포스팅이 없습니다.")

elif page == "카페":
    st.header("☕ 네이버 카페글 검색 및 커뮤니티 분석")
    
    with st.spinner("카페 포스팅 수집 중..."):
        try:
            all_cafes = fetch_cafe_data(run_kws)
        except Exception as e:
            st.error(f"카페 데이터 수집 실패: {e}")
            all_cafes = []
                    
    if all_cafes:
        df = pd.DataFrame(all_cafes)
        df['title'] = df['title'].apply(clean_html)
        df['description'] = df['description'].apply(clean_html)
        
        # Top Cafe names
        st.subheader("📊 주요 활성화 카페 분포 (Top 10)")
        df_cafe = df['cafename'].value_counts().reset_index().head(10)
        df_cafe.columns = ['cafename', 'count']
        fig = px.pie(
            df_cafe, values='count', names='cafename',
            title='가장 글이 많이 올라온 카페 분포'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Display table
        st.subheader("📋 카페 글 검색 리스트")
        st.dataframe(
            df[['title', 'description', 'cafename', 'search_keyword']],
            use_container_width=True
        )
    else:
        st.warning("조회된 카페 글이 없습니다.")

elif page == "뉴스":
    st.header("📰 네이버 뉴스 검색 및 미디어 분석")
    
    with st.spinner("최신 뉴스 수집 중..."):
        try:
            all_news = fetch_news_data(run_kws)
        except Exception as e:
            st.error(f"뉴스 데이터 수집 실패: {e}")
            all_news = []
                    
    if all_news:
        df = pd.DataFrame(all_news)
        df['title'] = df['title'].apply(clean_html)
        df['description'] = df['description'].apply(clean_html)
        
        # Extract publisher / media from URL or API
        def get_media_name(link):
            match = re.search(r'https?://(?:www\.)?([^/]+)', link)
            if match:
                domain = match.group(1)
                portal_map = {
                    'news.naver.com': '네이버뉴스',
                    'daum.net': '다음뉴스',
                    'chosun.com': '조선일보',
                    'donga.com': '동아일보',
                    'joins.com': '중앙일보',
                    'hankyung.com': '한국경제',
                    'mk.co.kr': '매일경제',
                    'hani.co.kr': '한겨레',
                    'khan.co.kr': '경향신문',
                    'yna.co.kr': '연합뉴스',
                    'nocutnews.co.kr': '노컷뉴스',
                    'sbs.co.kr': 'SBS',
                    'kbs.co.kr': 'KBS',
                    'imbc.com': 'MBC',
                    'ytn.co.kr': 'YTN'
                }
                for k, v in portal_map.items():
                    if k in domain:
                        return v
                return domain
            return '기타 미디어'
            
        df['media'] = df['link'].apply(get_media_name)
        
        # Media Share Pie Chart
        st.subheader("📊 주요 언론사 / 뉴스 포털 보도 비중 (Top 10)")
        df_media = df['media'].value_counts().reset_index().head(10)
        df_media.columns = ['media', 'count']
        fig = px.pie(
            df_media, values='count', names='media',
            title='검색된 뉴스 보도 언론사 비중'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Display table
        st.subheader("📋 뉴스 검색 리스트")
        st.dataframe(
            df[['title', 'description', 'media', 'pubDate', 'search_keyword']],
            use_container_width=True
        )
    else:
        st.warning("조회된 뉴스 데이터가 없습니다.")

elif page == "쇼핑 트렌드":
    st.header("📊 네이버 쇼핑 트렌드 비교 (데이터랩)")
    st.markdown("쇼핑 영역에서의 검색 키워드 인기도 및 트렌드 추이를 분석하여 비교합니다.")
    
    with st.spinner("쇼핑 트렌드 분석 중..."):
        try:
            # 트렌드 조회의 경우 기존 데이터랩 함수를 공통 사용
            data = fetch_keyword_trend(run_kws, run_start, run_end)
        except Exception as e:
            st.error(f"쇼핑 트렌드 수집 실패: {e}")
            data = None
        
    if data:
        all_data = []
        for grp in data.get("results", []):
            title = grp.get('title', grp.get('groupName'))
            for item in grp.get("data", []):
                all_data.append({
                    "period": item.get("period"),
                    "ratio": item.get("ratio"),
                    "keyword": title
                })
                
        if all_data:
            df = pd.DataFrame(all_data)
            df["period"] = pd.to_datetime(df["period"]).dt.date
            
            # Plotly Line Chart
            fig = px.line(
                df, x="period", y="ratio", color="keyword",
                title="일자별 쇼핑 관심도 추이 (상대값)",
                labels={"period": "날짜", "ratio": "쇼핑 검색 지수", "keyword": "검색어"},
                markers=True
            )
            fig.update_layout(hovermode="x unified", legend_title_text="키워드")
            st.plotly_chart(fig, use_container_width=True)
            
            # Pivot table
            df_pivot = df.pivot(index="period", columns="keyword", values="ratio").reset_index()
            st.subheader("📋 상세 쇼핑 관심도 수치")
            st.dataframe(df_pivot.set_index("period"), use_container_width=True)
        else:
            st.warning("조회된 트렌드 데이터가 없습니다.")
    else:
        st.warning("조회된 데이터가 없습니다.")

else:
    st.error("지원되지 않는 페이지입니다.")

# ---------- 실행 안내 ----------
st.caption("제작 및 배포: 네이버 API 기반 대시보드 - 캐싱 및 실행 제어 최적화 고도화 버전")
