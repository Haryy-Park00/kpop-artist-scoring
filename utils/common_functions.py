"""
크롤링 및 데이터 처리 공통 함수들
"""
import datetime
import time
import pandas as pd
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from typing import Tuple, Optional
from config import get_config
from utils.logging_config import get_project_logger
from utils.file_utils import safe_write_csv, safe_read_csv

logger = get_project_logger(__name__)


def get_current_week_info() -> Tuple[int, int, int]:
    """현재 년도와 주차 정보 반환"""
    now = datetime.datetime.now()
    year, week_number, weekday = now.isocalendar()
    return year, week_number, weekday


def safe_get_text(driver, xpath: str, default: str = "") -> str:
    """안전한 텍스트 추출 (레거시 함수들 통합)"""
    try:
        element = driver.find_element(By.XPATH, xpath)
        return element.text.strip() if element.text.strip() else default
    except NoSuchElementException:
        logger.debug(f"요소를 찾을 수 없음: {xpath}")
        return default


def save_dataframe_csv(df: pd.DataFrame, file_path: str, encoding: str = None) -> bool:
    """DataFrame을 CSV로 저장 (개선된 버전)"""
    file_config = get_config('file')
    encoding = encoding or file_config.get('csv_encoding', 'utf-8-sig')
    
    success = safe_write_csv(df, file_path, encoding=encoding)
    if success:
        logger.info(f"DataFrame CSV 저장 완료: {file_path}")
    return success


def read_dataframe_csv(file_path: str, encoding: str = None) -> Optional[pd.DataFrame]:
    """CSV 파일을 DataFrame으로 읽기 (개선된 버전)"""
    file_config = get_config('file')
    encoding = encoding or file_config.get('csv_encoding', 'utf-8-sig')
    
    df = safe_read_csv(file_path, encoding=encoding)
    if df is not None:
        logger.info(f"DataFrame CSV 로드 완료: {file_path}")
    return df


def process_numeric_string(value):
    """숫자+단위 문자열 처리 (sns_crawling.py에서 가져옴)"""
    if value is None:
        raise ValueError("Input value cannot be None")
    
    # 쉼표 제거
    value = value.replace(',', '')
    
    # 백만, 만, 천 단위 처리
    if '백만' in value:
        number = float(value.replace('백만', '').strip())
        return int(number * 1000000)
    elif '만' in value:
        number = float(value.replace('만', '').strip())
        return int(number * 10000)
    elif '천' in value:
        number = float(value.replace('천', '').strip())
        return int(number * 1000)
    elif '억' in value:
        number = float(value.replace('천', '').strip())
        return int(number * 100000000)
    
    else:
        try:
            return int(value)
        except ValueError:
            return 0


def clean_venue_name(venue_name):
    """공연장소명 정리 (venue_crawling.py에서 가져옴)"""
    if not venue_name:
        return ""
    
    # 괄호 제거
    cleaned = venue_name.split("(")[0]
    # 첫 번째 단어만 추출
    cleaned = cleaned.split()[0] if cleaned.split() else ""
    return cleaned.strip()


def create_performance_dataframe():
    """공연 정보용 기본 DataFrame 생성"""
    return pd.DataFrame(columns=[
        "공연명", "아티스트명", "장소", "年", "月", "日", 
        "티켓 가격", "좌석수", "시설특성", "위치", "홈페이지", "주관/주최", "기획"
    ])


def create_venue_dataframe():
    """공연장 정보용 기본 DataFrame 생성"""
    return pd.DataFrame(columns=[
        "공연장소", "객석수", "주소", "홈페이지"
    ])


def safe_sleep(seconds=1):
    """안전한 sleep (개발 시 조정 용이)"""
    time.sleep(seconds)


class DateTimeHelper:
    """날짜/시간 관련 유틸리티"""
    
    @staticmethod
    def get_today_string(format_str="%Y%m%d"):
        """오늘 날짜를 문자열로 반환"""
        return datetime.datetime.now().strftime(format_str)
    
    @staticmethod
    def get_week_string(year=None, week=None):
        """주차 문자열 생성"""
        if year is None or week is None:
            year, week, _ = get_current_week_info()
        return f"{year}년 {week}주차"
    
    @staticmethod
    def parse_date_range(date_string):
        """날짜 범위 문자열 파싱 (예: "2024.01.01 ~ 2024.12.31")"""
        if not date_string or ' ~ ' not in date_string:
            return [], []
            
        dates = date_string.split(' ~ ')
        months = []
        for date in dates:
            try:
                month = date.split('.')[1]
                months.append(month)
            except (IndexError, AttributeError):
                continue
                
        return dates, list(set(months))