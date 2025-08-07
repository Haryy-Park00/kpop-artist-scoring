"""
파일 처리 관련 공통 유틸리티 함수들
"""
import glob
import os
import pandas as pd
from pathlib import Path
from typing import Optional, List, Callable
import logging


def get_latest_file(pattern: str, key_func: Optional[Callable] = None) -> Optional[str]:
    """
    패턴에 맞는 최신 파일을 반환
    
    Args:
        pattern: 파일 검색 패턴 (glob 형식)
        key_func: 정렬 키 함수 (기본값: os.path.getmtime)
    
    Returns:
        최신 파일 경로 또는 None
    """
    try:
        files = glob.glob(pattern)
        if not files:
            return None
        
        if key_func is None:
            key_func = os.path.getmtime
            
        return max(files, key=key_func)
    except Exception as e:
        logging.error(f"최신 파일 검색 실패 ({pattern}): {e}")
        return None


def get_latest_files_by_pattern(patterns: List[str]) -> dict:
    """
    여러 패턴에 대해 최신 파일들을 반환
    
    Args:
        patterns: 파일 검색 패턴 리스트
    
    Returns:
        패턴별 최신 파일 경로 딕셔너리
    """
    result = {}
    for pattern in patterns:
        result[pattern] = get_latest_file(pattern)
    return result


def safe_read_csv(file_path: str, encoding: str = 'utf-8-sig', **kwargs) -> Optional[pd.DataFrame]:
    """
    안전한 CSV 파일 읽기
    
    Args:
        file_path: CSV 파일 경로
        encoding: 파일 인코딩
        **kwargs: pandas.read_csv 추가 옵션
    
    Returns:
        DataFrame 또는 None (실패 시)
    """
    try:
        if not os.path.exists(file_path):
            logging.warning(f"파일이 존재하지 않습니다: {file_path}")
            return None
            
        df = pd.read_csv(file_path, encoding=encoding, **kwargs)
        logging.info(f"CSV 파일 로드 성공: {file_path} ({len(df)}행)")
        return df
        
    except Exception as e:
        logging.error(f"CSV 파일 읽기 실패 ({file_path}): {e}")
        return None


def safe_write_csv(df: pd.DataFrame, file_path: str, encoding: str = 'utf-8-sig', 
                   create_dirs: bool = True, **kwargs) -> bool:
    """
    안전한 CSV 파일 쓰기
    
    Args:
        df: 저장할 DataFrame
        file_path: 저장할 파일 경로
        encoding: 파일 인코딩
        create_dirs: 디렉토리 자동 생성 여부
        **kwargs: pandas.to_csv 추가 옵션
    
    Returns:
        성공 여부
    """
    try:
        if create_dirs:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
        df.to_csv(file_path, index=False, encoding=encoding, **kwargs)
        logging.info(f"CSV 파일 저장 성공: {file_path} ({len(df)}행)")
        return True
        
    except Exception as e:
        logging.error(f"CSV 파일 저장 실패 ({file_path}): {e}")
        return False


def ensure_directory(path: str) -> bool:
    """
    디렉토리 존재 확인 및 생성
    
    Args:
        path: 디렉토리 경로
    
    Returns:
        성공 여부
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"디렉토리 생성 실패 ({path}): {e}")
        return False


def get_file_size(file_path: str) -> Optional[int]:
    """
    파일 크기 반환 (바이트)
    
    Args:
        file_path: 파일 경로
    
    Returns:
        파일 크기 또는 None
    """
    try:
        return os.path.getsize(file_path)
    except Exception:
        return None


def is_file_recent(file_path: str, max_age_hours: int = 24) -> bool:
    """
    파일이 최근 생성/수정되었는지 확인
    
    Args:
        file_path: 파일 경로
        max_age_hours: 최대 시간 (시간)
    
    Returns:
        최근 파일 여부
    """
    try:
        import time
        file_mtime = os.path.getmtime(file_path)
        current_time = time.time()
        age_hours = (current_time - file_mtime) / 3600
        return age_hours <= max_age_hours
    except Exception:
        return False


def cleanup_old_files(directory: str, pattern: str = "*", keep_count: int = 5) -> int:
    """
    오래된 파일들 정리
    
    Args:
        directory: 대상 디렉토리
        pattern: 파일 패턴
        keep_count: 유지할 파일 개수
    
    Returns:
        삭제된 파일 개수
    """
    try:
        search_pattern = os.path.join(directory, pattern)
        files = glob.glob(search_pattern)
        
        if len(files) <= keep_count:
            return 0
            
        # 수정 시간 기준 정렬 (최신순)
        files.sort(key=os.path.getmtime, reverse=True)
        
        # 오래된 파일들 삭제
        deleted_count = 0
        for file_path in files[keep_count:]:
            try:
                os.remove(file_path)
                deleted_count += 1
                logging.info(f"오래된 파일 삭제: {file_path}")
            except Exception as e:
                logging.error(f"파일 삭제 실패 ({file_path}): {e}")
                
        return deleted_count
        
    except Exception as e:
        logging.error(f"파일 정리 실패 ({directory}): {e}")
        return 0