import pandas as pd
import re

df = pd.read_csv("yes24/data/best_sellers.csv", encoding="utf-8-sig")

def parse_num(s):
    if pd.isna(s):
        return None
    cleaned = re.sub(r'[^\d]', '', str(s))
    return int(cleaned) if cleaned else None

df['판매가_숫자'] = df['판매가'].apply(parse_num)
df['정가_숫자'] = df['정가'].apply(parse_num)
df['판매지수_숫자'] = df['판매지수'].apply(parse_num)
df['리뷰수_숫자'] = pd.to_numeric(df['리뷰수'], errors='coerce')
df['평점_숫자'] = pd.to_numeric(df['평점'], errors='coerce')
df['출간연도'] = df['출간일'].str.extract(r'(\d{4})').astype(float)
df['출간월'] = df['출간일'].str.extract(r'(\d{1,2})월').astype(float)

keywords = ['AI', '클로드', '제미나이', '코딩', '교사', '바이브', '파이썬', '챗GPT', '엑셀', '유튜브']

lines = []
lines.append("=" * 60)
lines.append("YES24 IT/컴퓨터 베스트셀러 EDA 리포트")
lines.append("기준일: 2026년 06월 15일 | 카테고리: IT/컴퓨터")
lines.append("=" * 60)

lines.append("")
lines.append("[ 1. 데이터셋 기본 정보 ]")
lines.append(f"  - 수집 도서 수   : {len(df)}권")
lines.append(f"  - 수집 컬럼 수   : {len(df.columns)}개")
lines.append(f"  - 결측값 현황    :")
missing = df[['리뷰수', '평점', '부제목', '구매혜택', '배송정보']].isna().sum()
for col, cnt in missing.items():
    if cnt > 0:
        lines.append(f"      {col}: {cnt}건 ({cnt/len(df)*100:.0f}%)")

lines.append("")
lines.append("[ 2. 출판사 점유율 ]")
pub_counts = df['출판사'].value_counts()
for pub, cnt in pub_counts.items():
    bar = '■' * cnt
    lines.append(f"  {pub:<20} {bar} {cnt}권 ({cnt/len(df)*100:.0f}%)")

lines.append("")
lines.append("[ 3. 도서명 키워드 빈도 ]")
kw_counts = {kw: int(df['도서명'].str.contains(kw, case=False, na=False).sum()) for kw in keywords}
kw_sorted = sorted(kw_counts.items(), key=lambda x: -x[1])
for kw, cnt in kw_sorted:
    if cnt > 0:
        bar = '■' * cnt
        lines.append(f"  {kw:<8} {bar} {cnt}권")

lines.append("")
lines.append("[ 4. 가격 현황 ]")
lines.append(f"  평균 판매가  : {df['판매가_숫자'].mean():>10,.0f}원")
lines.append(f"  최저 판매가  : {df['판매가_숫자'].min():>10,}원")
lines.append(f"  최고 판매가  : {df['판매가_숫자'].max():>10,}원")
lines.append(f"  중앙값       : {df['판매가_숫자'].median():>10,.0f}원")
lines.append("")
lines.append("  가격대 분포:")
bins = [0, 15000, 20000, 25000, 30000, 35000, 50000]
labels_bin = ['~1.5만', '1.5~2만', '2~2.5만', '2.5~3만', '3~3.5만', '3.5만~']
df['가격구간'] = pd.cut(df['판매가_숫자'], bins=bins, labels=labels_bin)
for label, cnt in df['가격구간'].value_counts().sort_index().items():
    bar = '■' * cnt
    lines.append(f"  {label:<8} {bar} {cnt}권")

lines.append("")
lines.append("[ 5. 출간 시기 분포 ]")
yr_counts = df['출간연도'].value_counts().sort_index()
for yr, cnt in yr_counts.items():
    bar = '■' * cnt
    lines.append(f"  {int(yr)}년  {bar} {cnt}권")
yr2026 = int((df['출간연도'] == 2026).sum())
lines.append(f"  → 2026년 신간 비율: {yr2026/len(df)*100:.0f}% ({yr2026}권)")

lines.append("")
lines.append("[ 6. 판매지수 Top 10 ]")
top10 = df.nlargest(10, '판매지수_숫자')[['순위', '도서명', '판매지수_숫자', '평점_숫자']].reset_index(drop=True)
for i, row in top10.iterrows():
    name = row['도서명'][:18]
    rating = f"{row['평점_숫자']}" if pd.notna(row['평점_숫자']) else "N/A"
    lines.append(f"  {i+1:>2}. [{int(row['순위']):>2}위] {name:<18} 판매지수 {int(row['판매지수_숫자']):>7,}  평점 {rating}")

lines.append("")
lines.append("[ 7. 평점 현황 ]")
rated = df.dropna(subset=['평점_숫자'])
lines.append(f"  평점 보유 도서  : {len(rated)}권 / 전체 {len(df)}권")
lines.append(f"  평균 평점       : {rated['평점_숫자'].mean():.2f}")
lines.append(f"  최저 평점       : {rated['평점_숫자'].min():.1f}  ({df.loc[rated['평점_숫자'].idxmin(), '도서명'][:20]})")
lines.append(f"  최고 평점       : {rated['평점_숫자'].max():.1f}")
lines.append(f"  평점 10.0 도서  : {(rated['평점_숫자'] == 10.0).sum()}권")

lines.append("")
lines.append("[ 8. 리뷰수 현황 ]")
reviewed = df.dropna(subset=['리뷰수_숫자'])
lines.append(f"  리뷰 보유 도서  : {len(reviewed)}권")
lines.append(f"  평균 리뷰수     : {reviewed['리뷰수_숫자'].mean():.0f}건")
lines.append(f"  최다 리뷰       : {int(reviewed['리뷰수_숫자'].max())}건  ({df.loc[reviewed['리뷰수_숫자'].idxmax(), '도서명'][:20]})")

lines.append("")
lines.append("[ 9. 핵심 인사이트 ]")
lines.append("  1) AI 도서 시장 폭발적 성장")
lines.append(f"     2026년 신간이 전체의 71%를 차지하며 올해 급격히 성장.")
lines.append("")
lines.append("  2) 클로드 vs 제미나이 경쟁 구도")
lines.append("     클로드 관련 7권 > 제미나이 5권으로 클로드 도서가 우세.")
lines.append("     그러나 판매지수 1~2위는 제미나이 도서가 차지.")
lines.append("")
lines.append("  3) 한빛미디어 독주")
lines.append("     24권 중 7권(29%)을 한빛미디어가 출간, 압도적 1위.")
lines.append("     골든래빗·이지스퍼블리싱이 각 4권(17%)으로 추격.")
lines.append("")
lines.append("  4) 가격 수렴")
lines.append("     전체 도서의 75%가 2~3만원대에 집중.")
lines.append("     평균 판매가 22,718원 (10% 할인 적용 기준).")
lines.append("")
lines.append("  5) 교사 타깃 도서 부상")
lines.append("     '교사' 키워드 4권 — AI 활용 교육 분야 신규 수요 확인.")

lines.append("")
lines.append("=" * 60)
lines.append("차트 파일: yes24/output/eda_charts.png")
lines.append("=" * 60)

report = "\n".join(lines)

with open("yes24/output/eda_report.txt", "w", encoding="utf-8") as f:
    f.write(report)

print("저장 완료: yes24/output/eda_report.txt")
