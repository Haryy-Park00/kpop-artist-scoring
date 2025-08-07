FROM python:3.9-slim

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    xvfb \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 권한 설정
RUN chmod +x run_collection.sh

# 환경변수 설정
ENV CHROME_DRIVER_PATH=/usr/bin/chromedriver
ENV DISPLAY=:99

# 데이터 디렉토리 생성
RUN mkdir -p data/sns_links data/follower data/integrated_social logs

# 기본 명령어
CMD ["python", "scheduler.py"]