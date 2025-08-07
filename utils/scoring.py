#!/usr/bin/env python3
"""
아티스트 스코어링 유틸리티 함수
"""
import pandas as pd
from typing import Dict, Any, Optional
from config import get_config
from utils.logging_config import get_project_logger

logger = get_project_logger(__name__)


def calculate_artist_score(row: pd.Series, custom_weights: Optional[Dict[str, float]] = None) -> float:
    """
    아티스트 종합 스코어 계산 (0-100 스케일)
    
    Args:
        row: 아티스트 데이터가 포함된 pandas Series
        custom_weights: 커스텀 가중치 (선택사항)
    
    Returns:
        계산된 스코어 (0-100)
    """
    scoring_config = get_config('scoring')
    
    # 가중치 설정 (커스텀 또는 기본값)
    weights = custom_weights or {
        'spotify_popularity': scoring_config.get('spotify_popularity_weight', 0.3),
        'instagram_followers': scoring_config.get('instagram_followers_weight', 0.25),
        'twitter_followers': scoring_config.get('twitter_followers_weight', 0.20),
        'spotify_followers': scoring_config.get('spotify_followers_weight', 0.25)
    }
    
    score = 0
    max_follower_threshold = 10_000_000  # 1천만 팔로워 = 100점
    
    try:
        # Spotify 인기도 (0-100)
        if pd.notna(row.get('popularity')):
            score += row['popularity'] * weights['spotify_popularity']
        
        # Instagram 팔로워
        instagram_score = _calculate_follower_score(
            row.get('instagram_followers', 0), max_follower_threshold
        )
        score += instagram_score * weights['instagram_followers']
        
        # Twitter 팔로워
        twitter_score = _calculate_follower_score(
            row.get('twitter_followers', 0), max_follower_threshold
        )
        score += twitter_score * weights['twitter_followers']
        
        # Spotify 팔로워
        spotify_score = _calculate_follower_score(
            row.get('spotify_followers', 0), max_follower_threshold
        )
        score += spotify_score * weights['spotify_followers']
        
        # 최종 점수 정규화
        min_score = scoring_config.get('min_score', 0)
        max_score = scoring_config.get('max_score', 100)
        normalized_score = max(min_score, min(max_score, score))
        
        return round(normalized_score, 2)
        
    except Exception as e:
        logger.error(f"스코어 계산 중 오류: {e}")
        return 0.0


def _calculate_follower_score(followers: int, max_threshold: int) -> float:
    """팔로워 수를 기반으로 점수 계산"""
    if not followers or pd.isna(followers) or followers <= 0:
        return 0.0
    
    return min(100.0, (followers / max_threshold) * 100)


def calculate_weighted_score(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    가중치 기반 점수 계산
    
    Args:
        scores: 카테고리별 점수
        weights: 카테고리별 가중치
    
    Returns:
        가중 평균 점수
    """
    if not scores or not weights:
        return 0.0
    
    total_weighted_score = 0
    total_weight = 0
    
    for category, score in scores.items():
        weight = weights.get(category, 0)
        total_weighted_score += score * weight
        total_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    return total_weighted_score / total_weight


def normalize_score(score: float, min_val: float = 0, max_val: float = 100) -> float:
    """점수를 지정된 범위로 정규화"""
    return max(min_val, min(max_val, score))


def get_score_breakdown(row: pd.Series) -> Dict[str, Any]:
    """
    점수 세부사항 반환
    
    Args:
        row: 아티스트 데이터
    
    Returns:
        점수 구성 요소별 세부사항
    """
    scoring_config = get_config('scoring')
    max_threshold = 10_000_000
    
    breakdown = {
        'spotify_popularity': {
            'raw_value': row.get('popularity', 0),
            'score': row.get('popularity', 0) if pd.notna(row.get('popularity')) else 0,
            'weight': scoring_config.get('spotify_popularity_weight', 0.3)
        },
        'instagram_followers': {
            'raw_value': row.get('instagram_followers', 0),
            'score': _calculate_follower_score(row.get('instagram_followers', 0), max_threshold),
            'weight': scoring_config.get('instagram_followers_weight', 0.25)
        },
        'twitter_followers': {
            'raw_value': row.get('twitter_followers', 0),
            'score': _calculate_follower_score(row.get('twitter_followers', 0), max_threshold),
            'weight': scoring_config.get('twitter_followers_weight', 0.20)
        },
        'spotify_followers': {
            'raw_value': row.get('spotify_followers', 0),
            'score': _calculate_follower_score(row.get('spotify_followers', 0), max_threshold),
            'weight': scoring_config.get('spotify_followers_weight', 0.25)
        }
    }
    
    # 가중치 적용된 점수 계산
    total_score = 0
    for category, data in breakdown.items():
        weighted_score = data['score'] * data['weight']
        breakdown[category]['weighted_score'] = weighted_score
        total_score += weighted_score
    
    breakdown['total_score'] = round(total_score, 2)
    return breakdown


def batch_calculate_scores(df: pd.DataFrame, score_column: str = 'calculated_score') -> pd.DataFrame:
    """
    DataFrame의 모든 행에 대해 일괄 점수 계산
    
    Args:
        df: 아티스트 데이터 DataFrame
        score_column: 점수를 저장할 컬럼명
    
    Returns:
        점수가 추가된 DataFrame
    """
    try:
        df = df.copy()
        df[score_column] = df.apply(calculate_artist_score, axis=1)
        logger.info(f"일괄 점수 계산 완료: {len(df)}개 아티스트")
        return df
    except Exception as e:
        logger.error(f"일괄 점수 계산 실패: {e}")
        return df