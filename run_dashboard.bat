@echo off

rem 기존 .venv 가 존재하므로 새로 만들지 않음
if not exist ".venv" (
    echo [1/3] Creating virtual environment with Python 3.12...
    .\venv\Scripts\python -m venv .venv
) else (
    echo [1/3] 가상환경 .venv 이미 존재합니다.
)

rem 가상환경 활성화
call .\.venv\Scripts\activate.bat

rem 패키지 설치
echo [2/3] Installing dependencies (streamlit, pandas, requests, plotly)...
pip install --upgrade pip
pip install streamlit pandas requests plotly

rem 스트림릿 실행
echo [3/3] Running Streamlit dashboard...
start "" streamlit run naver-api-app\streamlit_app.py
timeout /t 5 >nul && start "" http://localhost:8501
pause
