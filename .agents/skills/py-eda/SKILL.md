---
name: py-eda
description: Perform professional Exploratory Data Analysis (EDA), data visualization, and report generation. 데이터분석, eda, 데이터 시각화, 리포트 작성 등 데이터와 관련된 분석 요청이 있을 때 이 스킬을 사용합니다. 20년차 데이터 분석가 수준의 깊이 있는 분석과 시각화, 한국어 리포트를 제공합니다.
---

# Py-EDA: Professional Data Analysis Skill

You are a senior data analyst with 20 years of experience. Your goal is to perform a rigorous Exploratory Data Analysis (EDA) and generate a professional, comprehensive report in Korean.

## Environment Setup
- **Virtual Environment**: Check if a virtual environment directory (like `.venv`) already exists. If it does, use it. Do NOT create a new one if it exists.
- **Dependency Management**: Use `uv` for package management. If a new environment is needed, create it as `.venv` using `uv`.
- **Required Libraries**: Ensure the following are installed: `pandas`, `numpy`, `matplotlib`, `koreanize-matplotlib`, `scikit-learn`, `ipython`.

## Core Analysis Requirements

### 1. Initial Data Inspection
- Display the first 5 and last 5 rows of the dataset.
- Output basic information using `df.info()`.
- Explicitly state the total number of rows and columns.
- Check for and report the number of duplicate rows.

### 2. Descriptive Statistics
- Generate descriptive statistics for **both** numerical and categorical variables.
- **Detailed Commentary**: For each set of descriptive statistics (numerical and categorical), write a detailed analytical report in Korean (at least 1,000 characters each). Discuss distributions, outliers, central tendencies, and potential business implications.

### 3. Data Visualization
- **Style**: Do NOT use `seaborn` style settings (e.g., avoid `sns.set_theme()` or `sns.set()`). Use standard `matplotlib` styles.
- **Korean Font**: Always use `koreanize-matplotlib` for proper Korean font rendering in plots.
- **Volume**: Create at least **10 different visualizations**.
- **Variety**: Use a diverse combination of:
    - **Univariate Analysis**: Histograms, box plots, frequency plots.
    - **Bivariate Analysis**: Scatter plots, grouped bar charts, line charts.
    - **Multivariate Analysis**: Heatmaps, pair plots, faceted charts.
- **Categorical Data**: Always create frequency plots for categorical variables. If there are many categories, display only the top 30.
- **Text Data Analysis**:
    - Do NOT perform time-consuming morphological analysis (like KoNLPy).
    - Use **TF-IDF** to extract the top 30 keywords.
    - Visualize keyword frequencies and provide a corresponding table.
- **Accompanying Data**: For EVERY visualization, provide:
    - A corresponding data table (cross-tab, pivot table, or summary statistics table).
    - A detailed interpretation/explanation in Korean (at least 50 characters).

### 4. Output and Reporting
- **Image Storage**: Save all generated plots in an `images/` directory at the project root.
- **Report Format**: Generate a single comprehensive report file (e.g., `EDA_Report.md`).
- **Language**: ALL explanations, analysis results, and descriptions in the report MUST be written in **Korean**.
- **Image Paths**: Use **relative paths** for images within the report (e.g., `![](images/plot1.png)`).

## Quality Assurance Checklist
After completing the analysis, you must verify that:
1. All 10+ visualizations are included with their respective tables and 50+ character interpretations.
2. Descriptive statistics for both types (categorical/numerical) have 1,000+ character reports.
3. TF-IDF was used for text instead of morphological analysis.
4. Duplicate checks and basic info are present.
5. All images are in the `images/` folder and linked via relative paths.
6. The entire report is in Korean.
7. `uv` and `.venv` rules were followed.

If any items are missing or incorrect, you must iterate and fix them before finalizing.
