import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import re
import os
from collections import Counter

# 한글 폰트 설정
font_path = None
for f in fm.findSystemFonts(fontpaths=None, fontext='ttf'):
    if any(k in f for k in ['malgun', 'Malgun', 'NanumGothic', 'gulim', 'Gulim']):
        font_path = f
        break

if font_path:
    fm.fontManager.addfont(font_path)
    font_name = fm.FontProperties(fname=font_path).get_name()
    plt.rcParams['font.family'] = font_name
else:
    plt.rcParams['font.family'] = 'Malgun Gothic'

plt.rcParams['axes.unicode_minus'] = False

# 데이터 로드
df = pd.read_csv("yes24/data/best_sellers.csv", encoding="utf-8-sig")

# 숫자 변환
def parse_num(s):
    if pd.isna(s):
        return None
    return int(re.sub(r'[^\d]', '', str(s))) if re.sub(r'[^\d]', '', str(s)) else None

df['판매가_숫자'] = df['판매가'].apply(parse_num)
df['정가_숫자'] = df['정가'].apply(parse_num)
df['판매지수_숫자'] = df['판매지수'].apply(parse_num)
df['리뷰수_숫자'] = pd.to_numeric(df['리뷰수'], errors='coerce')
df['평점_숫자'] = pd.to_numeric(df['평점'], errors='coerce')

# 출간 연도 추출
df['출간연도'] = df['출간일'].str.extract(r'(\d{4})').astype(float)
df['출간월'] = df['출간일'].str.extract(r'(\d{2})월').astype(float)

os.makedirs("yes24/output", exist_ok=True)

fig, axes = plt.subplots(3, 2, figsize=(16, 18))
fig.suptitle('YES24 IT/컴퓨터 베스트셀러 시장 현황 (2026.06 기준)', fontsize=16, fontweight='bold', y=0.98)

# 1. 출판사별 점유율
ax1 = axes[0, 0]
pub_counts = df['출판사'].value_counts()
colors = sns.color_palette("Set3", len(pub_counts))
wedges, texts, autotexts = ax1.pie(
    pub_counts.values,
    labels=None,
    autopct=lambda p: f'{p:.0f}%' if p >= 4 else '',
    colors=colors,
    startangle=140,
    pctdistance=0.75
)
legend_labels = [f'{pub} ({cnt}권)' for pub, cnt in pub_counts.items()]
ax1.legend(wedges, legend_labels, loc='lower center', bbox_to_anchor=(0.5, -0.25),
           ncol=2, fontsize=8)
ax1.set_title('출판사별 점유율', fontweight='bold', pad=10)

# 2. 도서명 키워드 빈도
ax2 = axes[0, 1]
keywords = ['클로드', '제미나이', 'AI', '코딩', '바이브', '파이썬', '교사', '유튜브', '엑셀', '챗GPT']
keyword_counts = {kw: df['도서명'].str.contains(kw, case=False, na=False).sum() for kw in keywords}
keyword_counts = {k: v for k, v in keyword_counts.items() if v > 0}
kw_sorted = sorted(keyword_counts.items(), key=lambda x: -x[1])
kw_names, kw_vals = zip(*kw_sorted)
bars = ax2.barh(kw_names, kw_vals, color=sns.color_palette("Blues_r", len(kw_names)))
ax2.set_xlabel('도서 수')
ax2.set_title('도서명 핵심 키워드 빈도', fontweight='bold')
ax2.set_xlim(0, max(kw_vals) + 1)
for bar, val in zip(bars, kw_vals):
    ax2.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2, f'{val}권',
             va='center', fontsize=9)

# 3. 판매지수 Top 10
ax3 = axes[1, 0]
top10 = df.nlargest(10, '판매지수_숫자')[['도서명', '판매지수_숫자']].copy()
top10['도서명_short'] = top10['도서명'].str[:14] + '...'
colors_bar = sns.color_palette("YlOrRd_r", 10)
bars3 = ax3.barh(range(len(top10)), top10['판매지수_숫자'].values, color=colors_bar)
ax3.set_yticks(range(len(top10)))
ax3.set_yticklabels(top10['도서명_short'].values, fontsize=8)
ax3.set_xlabel('판매지수')
ax3.set_title('판매지수 Top 10', fontweight='bold')
ax3.invert_yaxis()
for bar, val in zip(bars3, top10['판매지수_숫자'].values):
    ax3.text(bar.get_width() + 500, bar.get_y() + bar.get_height()/2,
             f'{val:,}', va='center', fontsize=8)

# 4. 가격대 분포
ax4 = axes[1, 1]
bins = [0, 15000, 20000, 25000, 30000, 35000, 40000]
labels_bin = ['~1.5만', '1.5~2만', '2~2.5만', '2.5~3만', '3~3.5만', '3.5만~']
df['가격구간'] = pd.cut(df['판매가_숫자'], bins=bins, labels=labels_bin)
price_dist = df['가격구간'].value_counts().sort_index()
ax4.bar(price_dist.index.astype(str), price_dist.values,
        color=sns.color_palette("Greens", len(price_dist)), edgecolor='white')
ax4.set_xlabel('판매가 구간')
ax4.set_ylabel('도서 수')
ax4.set_title('가격대 분포', fontweight='bold')
for i, v in enumerate(price_dist.values):
    ax4.text(i, v + 0.1, f'{v}권', ha='center', fontsize=9)

# 5. 출간 시기 트렌드 (연월별)
ax5 = axes[2, 0]
yr_counts = df['출간연도'].value_counts().sort_index()
yr_labels = [f'{int(y)}년' for y in yr_counts.index]
ax5.bar(yr_labels, yr_counts.values,
        color=sns.color_palette("Purples", len(yr_labels)), edgecolor='white')
ax5.set_ylabel('도서 수')
ax5.set_title('출간 연도 분포', fontweight='bold')
for i, v in enumerate(yr_counts.values):
    ax5.text(i, v + 0.1, f'{v}권', ha='center', fontsize=10)

# 6. 평점 vs 판매지수 (scatter)
ax6 = axes[2, 1]
valid = df.dropna(subset=['평점_숫자', '판매지수_숫자'])
scatter = ax6.scatter(
    valid['평점_숫자'],
    valid['판매지수_숫자'],
    c=valid['판매지수_숫자'],
    cmap='RdYlGn',
    s=valid['리뷰수_숫자'].fillna(10) * 0.8 + 20,
    alpha=0.8,
    edgecolors='gray', linewidth=0.5
)
for _, row in valid.iterrows():
    if row['판매지수_숫자'] > 30000:
        ax6.annotate(
            row['도서명'][:8],
            (row['평점_숫자'], row['판매지수_숫자']),
            fontsize=7, ha='center', va='bottom',
            xytext=(0, 5), textcoords='offset points'
        )
ax6.set_xlabel('평점')
ax6.set_ylabel('판매지수')
ax6.set_title('평점 vs 판매지수\n(원 크기 = 리뷰수)', fontweight='bold')
plt.colorbar(scatter, ax=ax6, label='판매지수')

plt.tight_layout()
plt.savefig("yes24/output/eda_charts.png", dpi=150, bbox_inches='tight', facecolor='white')
print("저장 완료: yes24/output/eda_charts.png")

# 텍스트 인사이트 출력
print("\n=== AI/코딩 도서 시장 핵심 인사이트 ===")
print(f"\n[1] 출판사 점유율")
for pub, cnt in pub_counts.items():
    print(f"  {pub}: {cnt}권 ({cnt/len(df)*100:.0f}%)")

print(f"\n[2] 키워드 트렌드")
for kw, cnt in kw_sorted:
    print(f"  '{kw}' 언급: {cnt}권")

print(f"\n[3] 가격 현황")
print(f"  평균 판매가: {df['판매가_숫자'].mean():,.0f}원")
print(f"  최저가: {df['판매가_숫자'].min():,}원 / 최고가: {df['판매가_숫자'].max():,}원")

print(f"\n[4] 출간 시기")
yr2025 = (df['출간연도'] == 2025).sum()
yr2026 = (df['출간연도'] == 2026).sum()
print(f"  2025년 출간: {yr2025}권 / 2026년 출간: {yr2026}권")
print(f"  → 2026년 신간이 전체의 {yr2026/len(df)*100:.0f}%")

print(f"\n[5] 판매 상위 3권")
for _, row in df.nlargest(3, '판매지수_숫자').iterrows():
    print(f"  {int(row['순위'])}위 {row['도서명'][:20]} - 판매지수 {int(row['판매지수_숫자']):,}")
