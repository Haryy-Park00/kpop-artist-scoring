"""
에러 처리 및 재시도 로직 관련 유틸리티
"""
import time
import logging
import functools
from typing import Any, Callable, Optional, Type, Tuple
import requests
from selenium.common.exceptions import WebDriverException


def with_retry(max_attempts: int = 3, delay: float = 1, 
               backoff_factor: float = 2, exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    함수 실행 시 실패하면 재시도하는 데코레이터
    
    Args:
        max_attempts: 최대 시도 횟수
        delay: 초기 대기 시간 (초)
        backoff_factor: 대기 시간 증가 배수
        exceptions: 재시도할 예외 타입들
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        logging.error(f"모든 재시도 실패 ({func.__name__}): {e}")
                        raise
                    
                    logging.warning(f"시도 {attempt + 1}/{max_attempts} 실패 ({func.__name__}): {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
                    
            return None
        return wrapper
    return decorator


def handle_api_error(func: Callable) -> Callable:
    """
    API 호출 에러 처리 데코레이터
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            logging.error(f"API 타임아웃 ({func.__name__})")
            return None
        except requests.exceptions.ConnectionError:
            logging.error(f"API 연결 오류 ({func.__name__})")
            return None
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP 오류 ({func.__name__}): {e.response.status_code}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"API 요청 오류 ({func.__name__}): {e}")
            return None
        except Exception as e:
            logging.error(f"예상치 못한 API 오류 ({func.__name__}): {e}")
            return None
    return wrapper


def handle_selenium_error(func: Callable) -> Callable:
    """
    Selenium 에러 처리 데코레이터
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except WebDriverException as e:
            logging.error(f"WebDriver 오류 ({func.__name__}): {e}")
            return None
        except Exception as e:
            logging.error(f"크롤링 오류 ({func.__name__}): {e}")
            return None
    return wrapper


def safe_execute(func: Callable, default_value: Any = None, 
                log_error: bool = True, error_message: Optional[str] = None) -> Any:
    """
    함수를 안전하게 실행하고 에러 시 기본값 반환
    
    Args:
        func: 실행할 함수
        default_value: 에러 시 반환할 기본값
        log_error: 에러 로깅 여부
        error_message: 커스텀 에러 메시지
    
    Returns:
        함수 실행 결과 또는 기본값
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            message = error_message or f"함수 실행 실패 ({func.__name__ if hasattr(func, '__name__') else 'unknown'})"
            logging.error(f"{message}: {e}")
        return default_value


class ErrorCollector:
    """에러 수집기 - 여러 에러를 모아서 처리"""
    
    def __init__(self):
        self.errors = []
    
    def add_error(self, error: Exception, context: str = ""):
        """에러 추가"""
        self.errors.append({
            'error': error,
            'context': context,
            'timestamp': time.time()
        })
    
    def has_errors(self) -> bool:
        """에러 존재 여부"""
        return len(self.errors) > 0
    
    def get_error_summary(self) -> str:
        """에러 요약 반환"""
        if not self.errors:
            return "에러 없음"
        
        summary = f"총 {len(self.errors)}개의 에러 발생:\n"
        for i, error_info in enumerate(self.errors, 1):
            summary += f"{i}. {error_info['context']}: {error_info['error']}\n"
        
        return summary
    
    def clear(self):
        """에러 목록 초기화"""
        self.errors.clear()


def validate_required_env_vars(required_vars: list) -> Tuple[bool, list]:
    """
    필수 환경변수 검증
    
    Args:
        required_vars: 필수 환경변수 리스트
    
    Returns:
        (모든 변수 존재 여부, 누락된 변수 리스트)
    """
    import os
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return len(missing_vars) == 0, missing_vars


def handle_quota_exceeded(func: Callable) -> Callable:
    """
    API 할당량 초과 처리 데코레이터
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                logging.error(f"API 할당량 초과 ({func.__name__})")
                return None
            elif e.response.status_code == 403:  # Forbidden
                logging.error(f"API 접근 권한 없음 ({func.__name__})")
                return None
            else:
                raise
        except Exception:
            raise
    return wrapper