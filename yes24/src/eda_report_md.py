import pandas as pd
import re
import base64

df = pd.read_csv("yes24/data/best_sellers.csv", encoding="utf-8-sig")

def parse_num(s):
    if pd.isna(s):
        return None
    cleaned = re.sub(r'[^\d]', '', str(s))
    return int(cleaned) if cleaned else None

df['판매가_숫자'] = df['판매가'].apply(parse_num)
df['판매지수_숫자'] = df['판매지수'].apply(parse_num)
df['리뷰수_숫자'] = pd.to_numeric(df['리뷰수'], errors='coerce')
df['평점_숫자'] = pd.to_numeric(df['평점'], errors='coerce')
df['출간연도'] = df['출간일'].str.extract(r'(\d{4})').astype(float)

keywords = ['AI', '클로드', '제미나이', '코딩', '교사', '바이브', '파이썬', '챗GPT', '엑셀', '유튜브']
kw_counts = {kw: int(df['도서명'].str.contains(kw, case=False, na=False).sum()) for kw in keywords}
kw_sorted = sorted(kw_counts.items(), key=lambda x: -x[1])

pub_counts = df['출판사'].value_counts()
yr_counts = df['출간연도'].value_counts().sort_index()
top10 = df.nlargest(10, '판매지수_숫자')[['순위', '도서명', '출판사', '판매지수_숫자', '평점_숫자']].reset_index(drop=True)
rated = df.dropna(subset=['평점_숫자'])
reviewed = df.dropna(subset=['리뷰수_숫자'])

bins = [0, 15000, 20000, 25000, 30000, 35000, 50000]
labels_bin = ['~1.5만', '1.5~2만', '2~2.5만', '2.5~3만', '3~3.5만', '3.5만~']
df['가격구간'] = pd.cut(df['판매가_숫자'], bins=bins, labels=labels_bin)
price_dist = df['가격구간'].value_counts().sort_index()

# 차트 이미지 base64 인코딩
with open("yes24/output/eda_charts.png", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

lines = []
lines.append("# YES24 IT/컴퓨터 베스트셀러 EDA 리포트")
lines.append("")
lines.append("> **기준일**: 2026년 06월 15일 | **카테고리**: IT/컴퓨터 > 컴퓨터/IT활용")
lines.append("")
lines.append("---")

# 1. 데이터셋 기본 정보
lines.append("")
lines.append("## 1. 데이터셋 기본 정보")
lines.append("")
lines.append(f"| 항목 | 값 |")
lines.append(f"|------|-----|")
lines.append(f"| 수집 도서 수 | {len(df)}권 |")
lines.append(f"| 수집 컬럼 수 | {len(df.columns)}개 |")
lines.append(f"| 할인율 | 전 도서 10% 동일 |")
lines.append(f"| 평균 판매가 | {df['판매가_숫자'].mean():,.0f}원 |")
lines.append(f"| 평점 보유 도서 | {len(rated)}권 |")
lines.append(f"| 리뷰 보유 도서 | {len(reviewed)}권 |")
lines.append("")
lines.append("**결측값 현황**")
lines.append("")
lines.append("| 컬럼 | 결측 건수 | 비율 |")
lines.append("|------|----------|------|")
for col in ['리뷰수', '평점', '부제목', '구매혜택', '배송정보']:
    cnt = df[col].isna().sum()
    lines.append(f"| {col} | {cnt}건 | {cnt/len(df)*100:.0f}% |")

# 2. 출판사
lines.append("")
lines.append("## 2. 출판사 점유율")
lines.append("")
lines.append("| 순위 | 출판사 | 도서 수 | 점유율 | 비율 |")
lines.append("|------|--------|--------|--------|------|")
for rank, (pub, cnt) in enumerate(pub_counts.items(), 1):
    bar = '█' * cnt + '░' * (7 - cnt)
    lines.append(f"| {rank} | {pub} | {cnt}권 | {bar} | {cnt/len(df)*100:.0f}% |")

# 3. 키워드
lines.append("")
lines.append("## 3. 도서명 키워드 빈도")
lines.append("")
lines.append("| 키워드 | 도서 수 | 빈도 |")
lines.append("|--------|--------|------|")
for kw, cnt in kw_sorted:
    if cnt > 0:
        bar = '█' * cnt + '░' * (8 - cnt)
        lines.append(f"| `{kw}` | {cnt}권 | {bar} |")

# 4. 가격
lines.append("")
lines.append("## 4. 가격 현황")
lines.append("")
lines.append("| 항목 | 금액 |")
lines.append("|------|------|")
lines.append(f"| 평균 판매가 | {df['판매가_숫자'].mean():,.0f}원 |")
lines.append(f"| 중앙값 | {df['판매가_숫자'].median():,.0f}원 |")
lines.append(f"| 최저가 | {df['판매가_숫자'].min():,}원 |")
lines.append(f"| 최고가 | {df['판매가_숫자'].max():,}원 |")
lines.append("")
lines.append("**가격대 분포**")
lines.append("")
lines.append("| 가격대 | 도서 수 | 비율 |")
lines.append("|--------|--------|------|")
for label, cnt in price_dist.items():
    lines.append(f"| {label} | {cnt}권 | {cnt/len(df)*100:.0f}% |")

# 5. 출간 시기
lines.append("")
lines.append("## 5. 출간 시기 분포")
lines.append("")
lines.append("| 연도 | 도서 수 | 비율 |")
lines.append("|------|--------|------|")
for yr, cnt in yr_counts.items():
    lines.append(f"| {int(yr)}년 | {cnt}권 | {cnt/len(df)*100:.0f}% |")
yr2026 = int((df['출간연도'] == 2026).sum())
lines.append("")
lines.append(f"> 2026년 신간 비율: **{yr2026/len(df)*100:.0f}%** ({yr2026}권) — 올해 신규 출간이 압도적")

# 6. 판매지수 Top 10
lines.append("")
lines.append("## 6. 판매지수 Top 10")
lines.append("")
lines.append("| # | 순위 | 도서명 | 출판사 | 판매지수 | 평점 |")
lines.append("|---|------|--------|--------|---------|------|")
for i, row in top10.iterrows():
    rating = f"{row['평점_숫자']}" if pd.notna(row['평점_숫자']) else "-"
    lines.append(f"| {i+1} | {int(row['순위'])}위 | {row['도서명'][:22]} | {row['출판사']} | {int(row['판매지수_숫자']):,} | {rating} |")

# 7. 평점
lines.append("")
lines.append("## 7. 평점 현황")
lines.append("")
lines.append("| 항목 | 값 |")
lines.append("|------|-----|")
lines.append(f"| 평균 평점 | {rated['평점_숫자'].mean():.2f} |")
lines.append(f"| 최저 평점 | {rated['평점_숫자'].min():.1f} ({df.loc[rated['평점_숫자'].idxmin(), '도서명'][:16]}) |")
lines.append(f"| 최고 평점 | {rated['평점_숫자'].max():.1f} |")
lines.append(f"| 평점 10.0 도서 | {int((rated['평점_숫자'] == 10.0).sum())}권 |")
lines.append(f"| 평균 리뷰수 | {reviewed['리뷰수_숫자'].mean():.0f}건 |")
lines.append(f"| 최다 리뷰 | {int(reviewed['리뷰수_숫자'].max())}건 ({df.loc[reviewed['리뷰수_숫자'].idxmax(), '도서명'][:16]}) |")

# 8. 인사이트
lines.append("")
lines.append("## 8. 핵심 인사이트")
lines.append("")
lines.append("### 1) AI 도서 시장 폭발적 성장")
lines.append(f"2026년 신간이 전체의 **71%**를 차지. 1~2년 사이 AI 실용서 수요가 급증하며 시장 자체가 새로 형성되는 단계.")
lines.append("")
lines.append("### 2) 클로드 vs 제미나이 경쟁 구도")
lines.append("클로드 관련 도서 **7권** > 제미나이 **5권**으로 출판 종수는 클로드 우세.  ")
lines.append("그러나 **판매지수 1~2위는 제미나이 도서** — 기존 구글 사용자 기반이 실구매로 이어지는 중.")
lines.append("")
lines.append("### 3) 한빛미디어 독주")
lines.append("24권 중 **7권(29%)**을 한빛미디어가 출간. 골든래빗·이지스퍼블리싱이 각 4권(17%)으로 추격 중.")
lines.append("")
lines.append("### 4) 가격 수렴 현상")
lines.append("전체 도서의 **75%가 1.5~3만원대**에 집중. 10% 할인 후 평균 22,718원으로 실용서 가격대가 표준화.")
lines.append("")
lines.append("### 5) 교사 타깃 도서 부상")
lines.append("'교사' 키워드 도서 **4권** 진입 — AI 활용 교육 분야가 새로운 독자층으로 부상.")
lines.append("")
lines.append("### 6) 스테디셀러의 생존")
lines.append("2022~2023년 출간된 『진짜 쓰는 실무 엑셀』(리뷰 388건)·『Do it! 파이썬』이 여전히 Top 20 유지.  ")
lines.append("AI 신간 홍수 속에서도 기초 실용서 수요는 꾸준함.")

# 9. 차트
lines.append("")
lines.append("## 9. EDA 차트")
lines.append("")
lines.append(f"![EDA 차트](data:image/png;base64,{img_b64})")
lines.append("")
lines.append("---")
lines.append("")
lines.append("*리포트 생성: yes24/src/eda_report_md.py | 데이터: yes24/data/best_sellers.csv*")

report = "\n".join(lines)
with open("yes24/output/eda_report.md", "w", encoding="utf-8") as f:
    f.write(report)

print("저장 완료: yes24/output/eda_report.md")
