"""
네이버 검색 API를 활용한 Streamlit 대시보드 애플리케이션 (고도화 버전 v2)

주요 기능:
- 총괄 요약(Overview) 대시보드: 모든 채널의 핵심 데이터를 한 화면에 표시
- 검색어 트렌드, 쇼핑, 블로그, 카페, 뉴스, 쇼핑 트렌드 등 6개 페이지 + 총괄 요약 1개 페이지
- 각 페이지별 심화 분석 (가격 분포, 시계열 추이, 키워드 빈도, 히트맵 등)
- UX 개선: CSV 다운로드, 정렬 옵션, 조회 건수 조절, 데이터 최신성 표시
- API 캐싱(st.cache_data), 세분화된 에러 핸들링, 보안 강화

고도화 변경 이력:
- v1: 기본 검색 및 시각화
- v2: 총괄 요약, 심화 분석, UX 개선, 에러 핸들링 강화
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import Counter
import re
import os
from dotenv import load_dotenv

# 로컬 개발 환경용 .env 파일 로드
load_dotenv()

# ========== 한국어 불용어 목록 (텍스트 빈도 분석용) ==========
STOPWORDS_KR = {
    "의", "가", "이", "은", "는", "들", "좀", "잘", "걍", "과", "도",
    "를", "으로", "자", "에", "와", "한", "하다", "에서", "및", "할",
    "수", "있는", "있다", "없다", "것", "등", "그", "저", "것이",
    "더", "때", "또", "대한", "했다", "위해", "된다", "하는", "합니다",
    "있습니다", "됩니다", "그리고", "하지만", "그런데", "따라서",
    "아주", "매우", "정말", "너무", "오늘", "이번", "대해", "통해",
    "위한", "따른", "관련", "중인", "위하여", "대하여",
    # 일반적인 검색 결과에서 의미 없는 단어들
    "the", "a", "an", "is", "are", "was", "in", "on", "at", "to", "for",
    "and", "or", "but", "with", "by", "from", "up", "about", "into",
}


# ========== API 키 조회 함수 ==========
def get_naver_api_key(key_name: str) -> str:
    """
    네이버 API 키를 조회하는 함수
    우선순위: 1. 환경변수/.env → 2. Streamlit Secrets
    """
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


# ========== API 키 로드 및 설정 ==========
default_client_id = get_naver_api_key("NAVER_CLIENT_ID")
default_client_secret = get_naver_api_key("NAVER_CLIENT_SECRET")

# ========== 페이지 기본 설정 ==========
st.set_page_config(
    page_title="네이버 API 대시보드",
    page_icon="🔍",
    layout="wide",
)

# ========== 사이드바 입력 ==========
st.sidebar.title("🔑 Naver API 설정")
client_id = st.sidebar.text_input(
    "Client ID",
    value=default_client_id,
    type="password" if default_client_id else "default",
)
client_secret = st.sidebar.text_input(
    "Client Secret",
    value=default_client_secret,
    type="password" if default_client_secret else "default",
)

st.sidebar.markdown("---")
st.sidebar.title("🔍 검색 옵션")
keywords_raw = st.sidebar.text_input("검색어 (콤마 구분)", "파이썬, 인공지능")

# 날짜 입력 (디폴트: 오늘 - 7일 ~ 오늘)
end_date = st.sidebar.date_input("종료 날짜", datetime.today())
start_date = st.sidebar.date_input("시작 날짜", datetime.today() - timedelta(days=7))

# 정렬 옵션 추가
sort_option = st.sidebar.selectbox(
    "정렬 방식",
    ["sim", "date"],
    format_func=lambda x: "정확도순" if x == "sim" else "날짜순",
)

# 조회 건수 옵션 추가
display_count = st.sidebar.selectbox(
    "조회 건수 (채널당)",
    [10, 30, 50, 100],
    index=1,  # 기본값 30
)

# 페이지 선택 (총괄 요약 추가)
page = st.sidebar.selectbox(
    "📊 대시보드 페이지",
    ["📋 총괄 요약", "검색어 트렌드", "쇼핑", "블로그", "카페", "뉴스", "쇼핑 트렌드"],
)


# ========== 헬퍼 함수 ==========
def _headers():
    """API 요청 헤더 생성"""
    return {
        "X-Naver-Client-Id": client_id.strip(),
        "X-Naver-Client-Secret": client_secret.strip(),
    }


def _parse_keywords(raw: str):
    """콤마 구분 키워드를 튜플로 변환"""
    return tuple([kw.strip() for kw in raw.split(",") if kw.strip()])


def clean_html(text):
    """HTML 태그 제거"""
    if not isinstance(text, str):
        return text
    return re.sub(r'<[^>]*>', '', text)


def extract_keywords_from_titles(titles, top_n=15):
    """
    제목 리스트에서 핵심 키워드를 추출하는 함수
    한국어 불용어 필터링 + 최소 2글자 이상 단어만 추출
    """
    all_words = []
    for title in titles:
        if not isinstance(title, str):
            continue
        # HTML 태그 제거 후 특수문자 제거
        cleaned = re.sub(r'[^\w\s]', ' ', clean_html(title))
        words = cleaned.split()
        for word in words:
            word = word.strip()
            if len(word) >= 2 and word.lower() not in STOPWORDS_KR:
                all_words.append(word)
    counter = Counter(all_words)
    return counter.most_common(top_n)


def handle_api_error(e, context="데이터"):
    """
    API 에러를 상태 코드별로 세분화하여 표시하는 함수
    """
    error_msg = str(e)
    if "401" in error_msg:
        st.error(f"🔑 {context} 수집 실패: API 키가 유효하지 않습니다. Client ID와 Client Secret을 확인해주세요.")
    elif "429" in error_msg:
        st.error(f"⏳ {context} 수집 실패: API 호출 한도(일 25,000회)를 초과했습니다. 잠시 후 다시 시도해주세요.")
    elif "403" in error_msg:
        st.error(f"🚫 {context} 수집 실패: 해당 API에 대한 접근 권한이 없습니다. 네이버 개발자센터에서 API 사용 신청을 확인해주세요.")
    elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
        st.error(f"🔧 {context} 수집 실패: 네이버 API 서버에 일시적 문제가 있습니다. 잠시 후 다시 시도해주세요.")
    elif "ConnectTimeout" in error_msg or "ReadTimeout" in error_msg or "Timeout" in error_msg:
        st.error(f"⏱️ {context} 수집 실패: API 응답 시간이 초과되었습니다. 네트워크 상태를 확인해주세요.")
    else:
        st.error(f"❌ {context} 수집 실패: {e}")


def show_data_info(df, channel_name=""):
    """조회 건수 및 데이터 최신성 표시"""
    col1, col2 = st.columns([1, 3])
    with col1:
        st.info(f"📊 총 **{len(df):,}건** 조회됨")
    with col2:
        st.caption(f"🕐 데이터 조회 시점: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def show_download_button(df, filename="data"):
    """CSV 다운로드 버튼 표시"""
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=f"naver_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=False,
    )


# ========== 캐싱 처리된 API 호출 함수들 ==========

@st.cache_data(ttl=3600)
def fetch_keyword_trend(keywords_tuple: tuple, start_date, end_date):
    """네이버 데이터랩 검색어 트렌드 API 호출"""
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
def fetch_shopping_data(keywords_tuple: tuple, sort: str = "sim", display: int = 30):
    """네이버 쇼핑 검색 API 호출"""
    base_url = "https://openapi.naver.com/v1/search/shop"
    all_items = []
    for kw in keywords_tuple:
        params = {"query": kw, "display": display, "start": 1, "sort": sort}
        resp = requests.get(base_url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            for item in data.get("items", []):
                item['search_keyword'] = kw
                all_items.append(item)
    return all_items


@st.cache_data(ttl=3600)
def fetch_blog_data(keywords_tuple: tuple, sort: str = "sim", display: int = 30):
    """네이버 블로그 검색 API 호출"""
    base_url = "https://openapi.naver.com/v1/search/blog"
    all_blogs = []
    for kw in keywords_tuple:
        params = {"query": kw, "display": display, "start": 1, "sort": sort}
        resp = requests.get(base_url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            for item in data.get("items", []):
                item['search_keyword'] = kw
                all_blogs.append(item)
    return all_blogs


@st.cache_data(ttl=3600)
def fetch_cafe_data(keywords_tuple: tuple, sort: str = "sim", display: int = 30):
    """네이버 카페글 검색 API 호출"""
    base_url = "https://openapi.naver.com/v1/search/cafearticle"
    all_cafes = []
    for kw in keywords_tuple:
        params = {"query": kw, "display": display, "start": 1, "sort": sort}
        resp = requests.get(base_url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            for item in data.get("items", []):
                item['search_keyword'] = kw
                all_cafes.append(item)
    return all_cafes


@st.cache_data(ttl=3600)
def fetch_news_data(keywords_tuple: tuple, sort: str = "sim", display: int = 50):
    """네이버 뉴스 검색 API 호출"""
    base_url = "https://openapi.naver.com/v1/search/news"
    all_news = []
    for kw in keywords_tuple:
        params = {"query": kw, "display": display, "start": 1, "sort": sort}
        resp = requests.get(base_url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            for item in data.get("items", []):
                item['search_keyword'] = kw
                all_news.append(item)
    return all_news


def get_media_name(link):
    """뉴스 URL에서 언론사 이름 추출"""
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
            'ytn.co.kr': 'YTN',
        }
        for k, v in portal_map.items():
            if k in domain:
                return v
        return domain
    return '기타 미디어'


# ========== API 호출 버튼 제어 및 세션 관리 ==========
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ 데이터 업데이트")

# 세션 상태 변수 초기화
if "run_analysis" not in st.session_state:
    st.session_state.run_analysis = False
if "last_keywords" not in st.session_state:
    st.session_state.last_keywords = None
if "last_start_date" not in st.session_state:
    st.session_state.last_start_date = None
if "last_end_date" not in st.session_state:
    st.session_state.last_end_date = None
if "last_sort" not in st.session_state:
    st.session_state.last_sort = None
if "last_display_count" not in st.session_state:
    st.session_state.last_display_count = None

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
            st.session_state.last_sort = sort_option
            st.session_state.last_display_count = display_count
with col2:
    if st.button("🔄 캐시 초기화", use_container_width=True):
        st.cache_data.clear()
        st.sidebar.success("캐시 초기화 완료!")
        st.rerun()

# 사이드바 하단: API 정보 안내
st.sidebar.markdown("---")
st.sidebar.caption(
    "ℹ️ **API 호출 한도 안내**\n\n"
    "- 검색 API: 일 **25,000회**\n"
    "- 데이터랩 API: 일 **1,000회**\n\n"
    "캐싱(1시간)이 적용되어 동일한 조건의 재조회 시 API를 소모하지 않습니다."
)


# ========== 메인 분석 로직 ==========
if not client_id or not client_secret:
    st.warning("API 키(Client ID, Client Secret)를 입력해주세요.")
    st.info("💡 사이드바에서 수동으로 입력하거나 로컬 환경의 `.env` 또는 배포 설정에 등록할 수 있습니다.")
    st.stop()

if not keywords:
    st.warning("검색어를 입력해주세요.")
    st.stop()

# 사용자가 아직 한 번도 분석 버튼을 누르지 않은 상태일 경우 안내
if not st.session_state.run_analysis:
    st.info("👈 왼쪽 사이드바에서 검색 옵션을 설정한 뒤 **[🔍 분석 실행]** 버튼을 눌러 시각화 분석을 시작하세요.")
    st.stop()

# 실행에 사용할 검색 옵션 바인딩
run_kws = st.session_state.last_keywords
run_start = st.session_state.last_start_date
run_end = st.session_state.last_end_date
run_sort = st.session_state.last_sort or "sim"
run_display = st.session_state.last_display_count or 30


# ================================================================
#                    📋 총괄 요약 (Overview) 페이지
# ================================================================
if page == "📋 총괄 요약":
    st.header("📋 총괄 요약 대시보드")
    st.markdown("모든 검색 채널의 핵심 데이터를 한 화면에서 파악합니다.")

    # 각 채널 데이터 수집
    overview_data = {}
    channel_errors = []

    with st.spinner("전 채널 데이터를 수집하는 중... (블로그, 뉴스, 쇼핑, 카페)"):
        # 블로그
        try:
            blog_items = fetch_blog_data(run_kws, run_sort, run_display)
            overview_data["블로그"] = blog_items
        except Exception as e:
            overview_data["블로그"] = []
            channel_errors.append(("블로그", e))

        # 뉴스
        try:
            news_items = fetch_news_data(run_kws, run_sort, run_display)
            overview_data["뉴스"] = news_items
        except Exception as e:
            overview_data["뉴스"] = []
            channel_errors.append(("뉴스", e))

        # 쇼핑
        try:
            shop_items = fetch_shopping_data(run_kws, run_sort, run_display)
            overview_data["쇼핑"] = shop_items
        except Exception as e:
            overview_data["쇼핑"] = []
            channel_errors.append(("쇼핑", e))

        # 카페
        try:
            cafe_items = fetch_cafe_data(run_kws, run_sort, run_display)
            overview_data["카페"] = cafe_items
        except Exception as e:
            overview_data["카페"] = []
            channel_errors.append(("카페", e))

    # 에러가 있는 채널 표시
    for ch_name, ch_error in channel_errors:
        handle_api_error(ch_error, ch_name)

    # ---------- KPI 카드 ----------
    st.subheader("📊 채널별 조회 건수")
    kpi_cols = st.columns(4)
    channel_icons = {"블로그": "📝", "뉴스": "📰", "쇼핑": "🛍️", "카페": "☕"}
    channel_counts = {}
    for idx, (ch_name, ch_items) in enumerate(overview_data.items()):
        count = len(ch_items)
        channel_counts[ch_name] = count
        with kpi_cols[idx]:
            st.metric(
                label=f"{channel_icons.get(ch_name, '📌')} {ch_name}",
                value=f"{count:,}건",
            )

    st.caption(f"🕐 데이터 조회 시점: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ---------- 채널별 비율 도넛 차트 ----------
    st.subheader("🍩 채널별 콘텐츠 비율")
    total_count = sum(channel_counts.values())
    if total_count > 0:
        donut_df = pd.DataFrame([
            {"채널": ch, "건수": cnt} for ch, cnt in channel_counts.items() if cnt > 0
        ])
        fig_donut = px.pie(
            donut_df, values="건수", names="채널",
            title=f"전체 {total_count:,}건 중 채널별 분포",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.warning("조회된 데이터가 없습니다.")

    # ---------- 트렌드 요약 (데이터랩) ----------
    st.subheader("📈 검색어 트렌드 요약")
    try:
        trend_data = fetch_keyword_trend(run_kws, run_start, run_end)
        all_trend = []
        for grp in trend_data.get("results", []):
            title = grp.get('title', grp.get('groupName'))
            for item in grp.get("data", []):
                all_trend.append({
                    "period": item.get("period"),
                    "ratio": item.get("ratio"),
                    "keyword": title,
                })
        if all_trend:
            df_trend = pd.DataFrame(all_trend)
            df_trend["period"] = pd.to_datetime(df_trend["period"]).dt.date
            fig_trend = px.line(
                df_trend, x="period", y="ratio", color="keyword",
                title="검색어 트렌드 추이 (데이터랩)",
                labels={"period": "날짜", "ratio": "검색량 비율", "keyword": "검색어"},
                markers=True,
            )
            fig_trend.update_layout(hovermode="x unified", legend_title_text="키워드", height=350)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("트렌드 데이터가 없습니다.")
    except Exception as e:
        handle_api_error(e, "트렌드")

    # ---------- 최근 핫 콘텐츠 Top 5 ----------
    st.subheader("🔥 채널별 최근 콘텐츠 Top 5")
    top_tabs = st.tabs(["📝 블로그", "📰 뉴스", "🛍️ 쇼핑", "☕ 카페"])

    # 블로그 Top 5
    with top_tabs[0]:
        if overview_data["블로그"]:
            df_blog_top = pd.DataFrame(overview_data["블로그"]).head(5)
            df_blog_top['title'] = df_blog_top['title'].apply(clean_html)
            for _, row in df_blog_top.iterrows():
                st.markdown(f"**[{row['title']}]({row.get('link', '#')})**")
                st.caption(f"👤 {row.get('bloggername', '-')} | 📅 {row.get('postdate', '-')} | 🏷️ {row.get('search_keyword', '-')}")
        else:
            st.info("블로그 데이터가 없습니다.")

    # 뉴스 Top 5
    with top_tabs[1]:
        if overview_data["뉴스"]:
            df_news_top = pd.DataFrame(overview_data["뉴스"]).head(5)
            df_news_top['title'] = df_news_top['title'].apply(clean_html)
            for _, row in df_news_top.iterrows():
                st.markdown(f"**[{row['title']}]({row.get('link', '#')})**")
                desc = clean_html(row.get('description', ''))
                st.caption(f"📅 {row.get('pubDate', '-')} | 🏷️ {row.get('search_keyword', '-')}")
        else:
            st.info("뉴스 데이터가 없습니다.")

    # 쇼핑 Top 5
    with top_tabs[2]:
        if overview_data["쇼핑"]:
            df_shop_top = pd.DataFrame(overview_data["쇼핑"]).head(5)
            df_shop_top['title'] = df_shop_top['title'].apply(clean_html)
            for _, row in df_shop_top.iterrows():
                price = pd.to_numeric(row.get('lprice', 0), errors='coerce')
                st.markdown(f"**[{row['title']}]({row.get('link', '#')})**")
                st.caption(f"💰 {int(price):,}원 | 🏪 {row.get('mallName', '-')} | 🏷️ {row.get('search_keyword', '-')}")
        else:
            st.info("쇼핑 데이터가 없습니다.")

    # 카페 Top 5
    with top_tabs[3]:
        if overview_data["카페"]:
            df_cafe_top = pd.DataFrame(overview_data["카페"]).head(5)
            df_cafe_top['title'] = df_cafe_top['title'].apply(clean_html)
            for _, row in df_cafe_top.iterrows():
                st.markdown(f"**[{row['title']}]({row.get('link', '#')})**")
                st.caption(f"☕ {row.get('cafename', '-')} | 🏷️ {row.get('search_keyword', '-')}")
        else:
            st.info("카페 데이터가 없습니다.")


# ================================================================
#                    📈 검색어 트렌드 페이지
# ================================================================
elif page == "검색어 트렌드":
    st.header("📈 네이버 검색어 트렌드 (데이터랩)")
    st.markdown("입력한 검색어들의 네이버 검색 트렌드를 비교 분석합니다. 가장 검색량이 높았던 시점을 100으로 설정한 상대값입니다.")

    with st.spinner("네이버 데이터랩 트렌드를 분석 중..."):
        try:
            data = fetch_keyword_trend(run_kws, run_start, run_end)
        except Exception as e:
            handle_api_error(e, "트렌드")
            data = None

    if data:
        all_data = []
        for grp in data.get("results", []):
            title = grp.get('title', grp.get('groupName'))
            for item in grp.get("data", []):
                all_data.append({
                    "period": item.get("period"),
                    "ratio": item.get("ratio"),
                    "keyword": title,
                })

        if all_data:
            df = pd.DataFrame(all_data)
            df["period"] = pd.to_datetime(df["period"]).dt.date

            show_data_info(df, "트렌드")

            # 라인 차트
            fig = px.line(
                df, x="period", y="ratio", color="keyword",
                title="일자별 검색어 트렌드 추이",
                labels={"period": "날짜", "ratio": "검색량 비율", "keyword": "검색어"},
                markers=True,
            )
            fig.update_layout(hovermode="x unified", legend_title_text="키워드")
            st.plotly_chart(fig, use_container_width=True)

            # 키워드별 평균/최대 검색량 비교 바 차트
            st.subheader("📊 키워드별 검색량 요약 비교")
            df_summary = df.groupby("keyword")["ratio"].agg(["mean", "max", "min"]).reset_index()
            df_summary.columns = ["keyword", "평균", "최대", "최소"]
            fig_summary = go.Figure()
            fig_summary.add_trace(go.Bar(name="평균", x=df_summary["keyword"], y=df_summary["평균"], marker_color="#636EFA"))
            fig_summary.add_trace(go.Bar(name="최대", x=df_summary["keyword"], y=df_summary["최대"], marker_color="#EF553B"))
            fig_summary.update_layout(
                barmode='group', title="키워드별 검색량 통계 비교",
                xaxis_title="키워드", yaxis_title="검색량 비율",
            )
            st.plotly_chart(fig_summary, use_container_width=True)

            # 피벗 테이블
            df_pivot = df.pivot(index="period", columns="keyword", values="ratio").reset_index()
            st.subheader("📋 상세 트렌드 수치")
            st.dataframe(df_pivot.set_index("period"), use_container_width=True)
            show_download_button(df_pivot, "trend")
        else:
            st.warning("조회된 트렌드 데이터가 없습니다.")


# ================================================================
#                    🛍️ 쇼핑 페이지
# ================================================================
elif page == "쇼핑":
    st.header("🛍️ 네이버 쇼핑 검색 및 가격 분석")

    with st.spinner("쇼핑 데이터를 수집하고 분석하는 중..."):
        try:
            all_items = fetch_shopping_data(run_kws, run_sort, run_display)
        except Exception as e:
            handle_api_error(e, "쇼핑")
            all_items = []

    if all_items:
        df = pd.DataFrame(all_items)
        df['title'] = df['title'].apply(clean_html)

        if 'lprice' in df.columns:
            df['price'] = pd.to_numeric(df['lprice'], errors='coerce')
            # hprice(최고가)도 가져오기
            if 'hprice' in df.columns:
                df['hprice_num'] = pd.to_numeric(df['hprice'], errors='coerce')

            show_data_info(df, "쇼핑")

            # ---------- KPI 카드 ----------
            st.subheader("💡 쇼핑 데이터 요약")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(label="최고가", value=f"{int(df['price'].max()):,}원")
            with col2:
                st.metric(label="최저가", value=f"{int(df['price'].min()):,}원")
            with col3:
                st.metric(label="평균가", value=f"{int(df['price'].mean()):,}원")
            with col4:
                st.metric(label="중앙값", value=f"{int(df['price'].median()):,}원")

            # ---------- 가격 분포 히스토그램 ----------
            st.subheader("📊 가격 분포 히스토그램")
            fig_hist = px.histogram(
                df, x="price", nbins=30, color="search_keyword",
                title="전체 상품 가격 분포",
                labels={"price": "가격 (원)", "search_keyword": "키워드", "count": "상품 수"},
                marginal="box",  # 위쪽에 박스플롯도 표시
                opacity=0.7,
            )
            fig_hist.update_layout(barmode="overlay")
            st.plotly_chart(fig_hist, use_container_width=True)

            # ---------- 키워드별 가격 박스플롯 ----------
            if len(run_kws) > 1:
                st.subheader("📦 키워드별 가격 비교 (박스플롯)")
                fig_box = px.box(
                    df, x="search_keyword", y="price",
                    title="키워드별 가격 범위 비교",
                    labels={"search_keyword": "키워드", "price": "가격 (원)"},
                    color="search_keyword",
                    points="outliers",
                )
                st.plotly_chart(fig_box, use_container_width=True)

            # ---------- 상위 10개 상품 가격 비교 ----------
            st.subheader("📊 상품별 가격 비교 (상위 10개)")
            df_top = df.sort_values(by="price", ascending=False).head(10)
            fig = px.bar(
                df_top, x="price", y="title", color="search_keyword",
                orientation="h",
                title="가장 높은 가격으로 등록된 상품 Top 10",
                labels={"price": "가격 (원)", "title": "상품명", "search_keyword": "키워드"},
                hover_data=["mallName"],
            )
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

            # ---------- 브랜드별 상품 수 Top 10 ----------
            st.subheader("🏷️ 브랜드별 상품 수 Top 10")
            if 'brand' in df.columns:
                df_brand = df[df['brand'].notna() & (df['brand'] != '')]['brand'].value_counts().reset_index().head(10)
                df_brand.columns = ['brand', 'count']
                if not df_brand.empty:
                    fig_brand = px.bar(
                        df_brand, x='count', y='brand', orientation='h',
                        title='시장 점유 브랜드 Top 10',
                        labels={'count': '상품 수', 'brand': '브랜드'},
                        color='count',
                        color_continuous_scale='Greens',
                    )
                    fig_brand.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_brand, use_container_width=True)
                else:
                    st.info("브랜드 정보가 있는 상품이 없습니다.")

            # ---------- 카테고리별 분포 ----------
            st.subheader("📂 카테고리별 상품 분포")
            cat_columns = [c for c in ['category1', 'category2', 'category3', 'category4'] if c in df.columns]
            if cat_columns:
                cat_col = st.selectbox("카테고리 레벨 선택", cat_columns, index=0)
                df_cat = df[df[cat_col].notna() & (df[cat_col] != '')][cat_col].value_counts().reset_index().head(15)
                df_cat.columns = ['category', 'count']
                if not df_cat.empty:
                    fig_cat = px.pie(
                        df_cat, values='count', names='category',
                        title=f'{cat_col} 기준 상품 분포',
                    )
                    st.plotly_chart(fig_cat, use_container_width=True)

            # ---------- 판매몰 분포 ----------
            st.subheader("🛒 주요 판매몰(Mall) 분포")
            df_mall = df['mallName'].value_counts().reset_index()
            df_mall.columns = ['mallName', 'count']
            fig_mall = px.pie(
                df_mall.head(15), values='count', names='mallName',
                title='상품이 가장 많이 등록된 쇼핑몰 분포',
            )
            st.plotly_chart(fig_mall, use_container_width=True)

            # ---------- 전체 리스트 ----------
            st.subheader("📋 전체 쇼핑 상품 리스트")
            display_cols = ['title', 'price', 'mallName', 'brand', 'search_keyword']
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True)
            show_download_button(df[display_cols], "shopping")
        else:
            st.warning("가격 데이터가 존재하지 않습니다.")
    else:
        st.warning("조회된 쇼핑 데이터가 없습니다.")


# ================================================================
#                    📝 블로그 페이지
# ================================================================
elif page == "블로그":
    st.header("📝 네이버 블로그 검색 및 포스팅 분석")

    with st.spinner("블로그 포스팅 수집 중..."):
        try:
            all_blogs = fetch_blog_data(run_kws, run_sort, run_display)
        except Exception as e:
            handle_api_error(e, "블로그")
            all_blogs = []

    if all_blogs:
        df = pd.DataFrame(all_blogs)
        df['title'] = df['title'].apply(clean_html)
        df['description'] = df['description'].apply(clean_html)

        show_data_info(df, "블로그")

        # ---------- 일자별 포스팅 추이 ----------
        st.subheader("📅 일자별 블로그 포스팅 추이")
        if 'postdate' in df.columns:
            df['post_date'] = pd.to_datetime(df['postdate'], format='%Y%m%d', errors='coerce')
            df_valid_date = df.dropna(subset=['post_date'])
            if not df_valid_date.empty:
                df_daily = df_valid_date.groupby([df_valid_date['post_date'].dt.date, 'search_keyword']).size().reset_index()
                df_daily.columns = ['date', 'keyword', 'count']
                fig_daily = px.line(
                    df_daily, x='date', y='count', color='keyword',
                    title='일자별 블로그 포스팅 수 추이',
                    labels={'date': '날짜', 'count': '포스팅 수', 'keyword': '키워드'},
                    markers=True,
                )
                fig_daily.update_layout(hovermode="x unified")
                st.plotly_chart(fig_daily, use_container_width=True)

        # ---------- 키워드별 블로거 수 비교 ----------
        if len(run_kws) > 1:
            st.subheader("👥 키워드별 고유 블로거 수 비교")
            blogger_counts = df.groupby('search_keyword')['bloggername'].nunique().reset_index()
            blogger_counts.columns = ['keyword', 'unique_bloggers']
            fig_bloggers = px.bar(
                blogger_counts, x='keyword', y='unique_bloggers',
                title='키워드별 콘텐츠를 작성한 고유 블로거 수',
                labels={'keyword': '키워드', 'unique_bloggers': '블로거 수'},
                color='unique_bloggers',
                color_continuous_scale='Blues',
            )
            st.plotly_chart(fig_bloggers, use_container_width=True)

        # ---------- 주요 블로거 분포 ----------
        st.subheader("📊 주요 블로거 분포 (Top 10)")
        df_blogger = df['bloggername'].value_counts().reset_index().head(10)
        df_blogger.columns = ['bloggername', 'count']
        fig = px.bar(
            df_blogger, x='count', y='bloggername', orientation='h',
            title='상위 블로그 포스터 분석',
            labels={'count': '포스트 개수', 'bloggername': '블로그명'},
            color='count',
            color_continuous_scale='Purples',
        )
        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

        # ---------- 제목 키워드 빈도 분석 ----------
        st.subheader("🔤 제목 핵심 키워드 빈도 (Top 15)")
        kw_freq = extract_keywords_from_titles(df['title'].tolist())
        if kw_freq:
            df_kw = pd.DataFrame(kw_freq, columns=['keyword', 'count'])
            fig_kw = px.bar(
                df_kw, x='count', y='keyword', orientation='h',
                title='블로그 제목에서 가장 자주 등장한 키워드',
                labels={'count': '등장 횟수', 'keyword': '키워드'},
                color='count',
                color_continuous_scale='Oranges',
            )
            fig_kw.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_kw, use_container_width=True)

        # ---------- 전체 리스트 ----------
        st.subheader("📋 블로그 검색 리스트")
        st.dataframe(
            df[['title', 'description', 'bloggername', 'postdate', 'search_keyword']],
            use_container_width=True,
        )
        show_download_button(df[['title', 'description', 'bloggername', 'postdate', 'search_keyword']], "blog")
    else:
        st.warning("조회된 블로그 포스팅이 없습니다.")


# ================================================================
#                    ☕ 카페 페이지
# ================================================================
elif page == "카페":
    st.header("☕ 네이버 카페글 검색 및 커뮤니티 분석")

    with st.spinner("카페 포스팅 수집 중..."):
        try:
            all_cafes = fetch_cafe_data(run_kws, run_sort, run_display)
        except Exception as e:
            handle_api_error(e, "카페")
            all_cafes = []

    if all_cafes:
        df = pd.DataFrame(all_cafes)
        df['title'] = df['title'].apply(clean_html)
        df['description'] = df['description'].apply(clean_html)

        show_data_info(df, "카페")

        # ---------- 키워드별 카페글 수 비교 ----------
        if len(run_kws) > 1:
            st.subheader("📊 키워드별 카페글 수 비교")
            kw_counts = df['search_keyword'].value_counts().reset_index()
            kw_counts.columns = ['keyword', 'count']
            fig_kw_cmp = px.bar(
                kw_counts, x='keyword', y='count',
                title='키워드별 카페글 콘텐츠 수 비교',
                labels={'keyword': '키워드', 'count': '글 수'},
                color='count',
                color_continuous_scale='Tealgrn',
            )
            st.plotly_chart(fig_kw_cmp, use_container_width=True)

        # ---------- 주요 카페 분포 ----------
        st.subheader("📊 주요 활성화 카페 분포 (Top 10)")
        df_cafe = df['cafename'].value_counts().reset_index().head(10)
        df_cafe.columns = ['cafename', 'count']
        fig = px.pie(
            df_cafe, values='count', names='cafename',
            title='가장 글이 많이 올라온 카페 분포',
        )
        st.plotly_chart(fig, use_container_width=True)

        # ---------- 제목 키워드 빈도 분석 ----------
        st.subheader("🔤 카페글 제목 핵심 키워드 빈도 (Top 15)")
        kw_freq = extract_keywords_from_titles(df['title'].tolist())
        if kw_freq:
            df_kw = pd.DataFrame(kw_freq, columns=['keyword', 'count'])
            fig_kw = px.bar(
                df_kw, x='count', y='keyword', orientation='h',
                title='카페글 제목에서 가장 자주 등장한 키워드',
                labels={'count': '등장 횟수', 'keyword': '키워드'},
                color='count',
                color_continuous_scale='Oranges',
            )
            fig_kw.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_kw, use_container_width=True)

        # ---------- 전체 리스트 ----------
        st.subheader("📋 카페 글 검색 리스트")
        st.dataframe(
            df[['title', 'description', 'cafename', 'search_keyword']],
            use_container_width=True,
        )
        show_download_button(df[['title', 'description', 'cafename', 'search_keyword']], "cafe")
    else:
        st.warning("조회된 카페 글이 없습니다.")


# ================================================================
#                    📰 뉴스 페이지
# ================================================================
elif page == "뉴스":
    st.header("📰 네이버 뉴스 검색 및 미디어 분석")

    with st.spinner("최신 뉴스 수집 중..."):
        try:
            all_news = fetch_news_data(run_kws, run_sort, run_display)
        except Exception as e:
            handle_api_error(e, "뉴스")
            all_news = []

    if all_news:
        df = pd.DataFrame(all_news)
        df['title'] = df['title'].apply(clean_html)
        df['description'] = df['description'].apply(clean_html)
        df['media'] = df['link'].apply(get_media_name)

        show_data_info(df, "뉴스")

        # ---------- 일자별 보도량 추이 ----------
        st.subheader("📅 일자별 뉴스 보도량 추이")
        if 'pubDate' in df.columns:
            df['pub_date'] = pd.to_datetime(df['pubDate'], errors='coerce')
            df_valid_date = df.dropna(subset=['pub_date'])
            if not df_valid_date.empty:
                df_daily = df_valid_date.groupby([df_valid_date['pub_date'].dt.date, 'search_keyword']).size().reset_index()
                df_daily.columns = ['date', 'keyword', 'count']
                fig_daily = px.bar(
                    df_daily, x='date', y='count', color='keyword',
                    title='일자별 뉴스 보도 건수',
                    labels={'date': '날짜', 'count': '보도 건수', 'keyword': '키워드'},
                    barmode='group',
                )
                fig_daily.update_layout(hovermode="x unified")
                st.plotly_chart(fig_daily, use_container_width=True)

        # ---------- 언론사 보도 비중 ----------
        st.subheader("📊 주요 언론사 / 뉴스 포털 보도 비중 (Top 10)")
        df_media = df['media'].value_counts().reset_index().head(10)
        df_media.columns = ['media', 'count']
        fig = px.pie(
            df_media, values='count', names='media',
            title='검색된 뉴스 보도 언론사 비중',
        )
        st.plotly_chart(fig, use_container_width=True)

        # ---------- 키워드 × 언론사 히트맵 ----------
        if len(run_kws) > 1:
            st.subheader("🗺️ 키워드 × 언론사 보도 히트맵")
            # 상위 언론사만 추출하여 히트맵 구성
            top_media = df['media'].value_counts().head(10).index.tolist()
            df_heatmap = df[df['media'].isin(top_media)]
            if not df_heatmap.empty:
                heatmap_data = df_heatmap.groupby(['search_keyword', 'media']).size().reset_index(name='count')
                heatmap_pivot = heatmap_data.pivot(index='search_keyword', columns='media', values='count').fillna(0)
                fig_heatmap = px.imshow(
                    heatmap_pivot,
                    title="키워드별 언론사 보도 건수 히트맵",
                    labels=dict(x="언론사", y="키워드", color="보도 건수"),
                    color_continuous_scale="YlOrRd",
                    aspect="auto",
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

        # ---------- 제목 키워드 빈도 분석 ----------
        st.subheader("🔤 뉴스 제목 핵심 키워드 빈도 (Top 15)")
        kw_freq = extract_keywords_from_titles(df['title'].tolist())
        if kw_freq:
            df_kw = pd.DataFrame(kw_freq, columns=['keyword', 'count'])
            fig_kw = px.bar(
                df_kw, x='count', y='keyword', orientation='h',
                title='뉴스 제목에서 가장 자주 등장한 키워드',
                labels={'count': '등장 횟수', 'keyword': '키워드'},
                color='count',
                color_continuous_scale='Reds',
            )
            fig_kw.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_kw, use_container_width=True)

        # ---------- 전체 리스트 ----------
        st.subheader("📋 뉴스 검색 리스트")
        st.dataframe(
            df[['title', 'description', 'media', 'pubDate', 'search_keyword']],
            use_container_width=True,
        )
        show_download_button(df[['title', 'description', 'media', 'pubDate', 'search_keyword']], "news")
    else:
        st.warning("조회된 뉴스 데이터가 없습니다.")


# ================================================================
#                    📊 쇼핑 트렌드 페이지
# ================================================================
elif page == "쇼핑 트렌드":
    st.header("📊 네이버 쇼핑 트렌드 비교 (데이터랩)")
    st.markdown("쇼핑 영역에서의 검색 키워드 인기도 및 트렌드 추이를 분석하여 비교합니다.")

    with st.spinner("쇼핑 트렌드 분석 중..."):
        try:
            data = fetch_keyword_trend(run_kws, run_start, run_end)
        except Exception as e:
            handle_api_error(e, "쇼핑 트렌드")
            data = None

    if data:
        all_data = []
        for grp in data.get("results", []):
            title = grp.get('title', grp.get('groupName'))
            for item in grp.get("data", []):
                all_data.append({
                    "period": item.get("period"),
                    "ratio": item.get("ratio"),
                    "keyword": title,
                })

        if all_data:
            df = pd.DataFrame(all_data)
            df["period"] = pd.to_datetime(df["period"]).dt.date

            show_data_info(df, "쇼핑 트렌드")

            # 라인 차트
            fig = px.line(
                df, x="period", y="ratio", color="keyword",
                title="일자별 쇼핑 관심도 추이 (상대값)",
                labels={"period": "날짜", "ratio": "쇼핑 검색 지수", "keyword": "검색어"},
                markers=True,
            )
            fig.update_layout(hovermode="x unified", legend_title_text="키워드")
            st.plotly_chart(fig, use_container_width=True)

            # 영역 차트 (면적 비교)
            st.subheader("📈 키워드별 관심도 영역 비교")
            fig_area = px.area(
                df, x="period", y="ratio", color="keyword",
                title="키워드별 쇼핑 관심도 영역 차트",
                labels={"period": "날짜", "ratio": "쇼핑 검색 지수", "keyword": "검색어"},
            )
            fig_area.update_layout(hovermode="x unified")
            st.plotly_chart(fig_area, use_container_width=True)

            # 피벗 테이블
            df_pivot = df.pivot(index="period", columns="keyword", values="ratio").reset_index()
            st.subheader("📋 상세 쇼핑 관심도 수치")
            st.dataframe(df_pivot.set_index("period"), use_container_width=True)
            show_download_button(df_pivot, "shopping_trend")
        else:
            st.warning("조회된 트렌드 데이터가 없습니다.")
    else:
        st.warning("조회된 데이터가 없습니다.")

else:
    st.error("지원되지 않는 페이지입니다.")


# ========== 하단 정보 ==========
st.markdown("---")
st.caption(
    f"제작 및 배포: 네이버 API 기반 대시보드 v2 (고도화 버전) | "
    f"검색어: {', '.join(run_kws)} | "
    f"정렬: {'정확도순' if run_sort == 'sim' else '날짜순'} | "
    f"채널당 조회 건수: {run_display}건"
)
