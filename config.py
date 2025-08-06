#!/usr/bin/env python3
"""
프로젝트 설정 파일
"""
import os
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent

# Chrome WebDriver 경로 (자동 감지)
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH', '/usr/local/bin/chromedriver')

# 데이터 저장 경로
DATA_PATH = PROJECT_ROOT / "data"
DATA_PATH.mkdir(exist_ok=True)

# 기본 설정
DEFAULT_SCORING_WEIGHTS = {
    "음악성": 25,
    "퍼포먼스": 25, 
    "비주얼": 20,
    "인기도": 15,
    "성장 가능성": 15
}