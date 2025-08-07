"""
로깅 설정 관리
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, level: int = logging.INFO, 
                log_file: str = None, console: bool = True) -> logging.Logger:
    """
    표준 로거 설정
    
    Args:
        name: 로거 이름
        level: 로그 레벨
        log_file: 로그 파일 경로 (None이면 파일 로그 비활성화)
        console: 콘솔 출력 여부
    
    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()
    
    logger.setLevel(level)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 파일 핸들러
    if log_file:
        # 로그 디렉토리 생성
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_project_logger(module_name: str) -> logging.Logger:
    """
    프로젝트 표준 로거 반환
    
    Args:
        module_name: 모듈 이름 (보통 __name__ 사용)
    
    Returns:
        설정된 로거
    """
    # 프로젝트 루트 기준 로그 파일 경로
    project_root = Path(__file__).parent.parent
    log_file = project_root / "logs" / f"kpop-artist-scoring-{datetime.now().strftime('%Y-%m-%d')}.log"
    
    return setup_logger(
        name=module_name,
        level=logging.INFO,
        log_file=str(log_file),
        console=True
    )


class ProgressLogger:
    """
    진행 상황 로깅을 위한 헬퍼 클래스
    """
    
    def __init__(self, logger: logging.Logger, total_items: int, log_interval: int = 10):
        self.logger = logger
        self.total_items = total_items
        self.log_interval = log_interval
        self.processed_count = 0
        self.start_time = datetime.now()
    
    def update(self, increment: int = 1, message: str = ""):
        """진행 상황 업데이트"""
        self.processed_count += increment
        
        if self.processed_count % self.log_interval == 0 or self.processed_count == self.total_items:
            progress_percent = (self.processed_count / self.total_items) * 100
            elapsed_time = datetime.now() - self.start_time
            
            log_message = f"진행률: {self.processed_count}/{self.total_items} ({progress_percent:.1f}%) "
            log_message += f"경과시간: {elapsed_time}"
            
            if message:
                log_message += f" - {message}"
            
            self.logger.info(log_message)
    
    def complete(self, message: str = ""):
        """완료 로깅"""
        total_time = datetime.now() - self.start_time
        complete_message = f"완료: {self.processed_count}/{self.total_items} 처리됨, 총 소요시간: {total_time}"
        
        if message:
            complete_message += f" - {message}"
        
        self.logger.info(complete_message)


def log_function_call(logger: logging.Logger):
    """
    함수 호출 로깅 데코레이터
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"함수 호출: {func.__name__}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"함수 완료: {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"함수 오류: {func.__name__} - {e}")
                raise
        return wrapper
    return decorator


def log_execution_time(logger: logging.Logger):
    """
    함수 실행 시간 로깅 데코레이터
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            logger.info(f"시작: {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = datetime.now() - start_time
                logger.info(f"완료: {func.__name__} (소요시간: {execution_time})")
                return result
            except Exception as e:
                execution_time = datetime.now() - start_time
                logger.error(f"오류: {func.__name__} (소요시간: {execution_time}) - {e}")
                raise
        return wrapper
    return decorator