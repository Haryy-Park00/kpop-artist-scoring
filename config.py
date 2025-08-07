#!/usr/bin/env python3
"""
프로젝트 설정 파일
"""
import os
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent

# Chrome WebDriver 경로 (자동 감지)
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH', '/usr/local/bin/chromedriver')

# 데이터 저장 경로
DATA_PATH = PROJECT_ROOT / "data"
LOGS_PATH = PROJECT_ROOT / "logs"
DATA_PATH.mkdir(exist_ok=True)
LOGS_PATH.mkdir(exist_ok=True)

# 크롤링 설정
CRAWLING_CONFIG = {
    'page_load_delay': 3,
    'request_interval': 2,
    'instagram_delay': 5,
    'twitter_delay': 10,
    'youtube_delay': 3,
    'naver_search_delay': 2,
    'max_retries': 3,
    'timeout': 30
}

# 스코어링 설정
SCORING_CONFIG = {
    'spotify_popularity_weight': 0.3,
    'instagram_followers_weight': 0.25,
    'twitter_followers_weight': 0.20,
    'spotify_followers_weight': 0.25,
    'min_score': 0,
    'max_score': 100
}

# 수동 평가 기본 가중치
DEFAULT_SCORING_WEIGHTS = {
    "음악성": 25,
    "퍼포먼스": 25, 
    "비주얼": 20,
    "인기도": 15,
    "성장 가능성": 15
}

# API 설정
API_CONFIG = {
    'spotify': {
        'base_url': 'https://api.spotify.com/v1',
        'token_url': 'https://accounts.spotify.com/api/token',
        'rate_limit': 100,  # requests per hour
        'timeout': 10
    },
    'youtube': {
        'base_url': 'https://www.googleapis.com/youtube/v3',
        'rate_limit': 10000,  # requests per day
        'timeout': 10
    }
}

# Chrome 드라이버 옵션
CHROME_OPTIONS = [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-blink-features=AutomationControlled',
    '--disable-web-security',
    '--disable-features=VizDisplayCompositor',
    '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
]

# 파일 처리 설정
FILE_CONFIG = {
    'csv_encoding': 'utf-8-sig',
    'max_file_age_days': 30,
    'backup_count': 5,
    'chunk_size': 1000
}

# 로깅 설정
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 3
}

# 환경별 설정 오버라이드
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

if ENVIRONMENT == 'production':
    CRAWLING_CONFIG['request_interval'] = 5  # 프로덕션에서는 더 보수적
    LOGGING_CONFIG['level'] = 'WARNING'
elif ENVIRONMENT == 'development':
    CRAWLING_CONFIG['request_interval'] = 1  # 개발에서는 빠르게
    LOGGING_CONFIG['level'] = 'DEBUG'

def get_config(section: str) -> Dict[str, Any]:
    """설정 섹션 반환"""
    configs = {
        'crawling': CRAWLING_CONFIG,
        'scoring': SCORING_CONFIG,
        'api': API_CONFIG,
        'file': FILE_CONFIG,
        'logging': LOGGING_CONFIG,
        'chrome': {'options': CHROME_OPTIONS, 'path': CHROME_DRIVER_PATH}
    }
    return configs.get(section, {})