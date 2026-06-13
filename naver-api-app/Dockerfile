# 1단계: 경량화된 Python 3.12 베이스 이미지 사용
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 라이브러리 업데이트 및 필요한 도구(curl 등) 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치 (루트 경로의 requirements.txt 복사)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# naver-api-app 디렉토리 내 소스코드 및 리소스 전체 복사
COPY naver-api-app/ .

# Streamlit 기본 포트(8501) 노출
EXPOSE 8501

# 컨테이너 상태 점검(헬스체크) 설정
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Streamlit 실행 (포트 및 주소 바인딩 설정)
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
