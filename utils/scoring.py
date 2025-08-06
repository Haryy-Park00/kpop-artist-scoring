#!/usr/bin/env python3
"""
아티스트 스코어링 유틸리티 함수
"""
import pandas as pd

def calculate_artist_score(row):
    """아티스트 종합 스코어 계산 (0-100 스케일)"""
    score = 0
    
    # Spotify 인기도 (0-100) - 30% 가중치
    if pd.notna(row.get('popularity')):
        score += row['popularity'] * 0.3
    
    # Instagram 팔로워 - 25% 가중치 (선형 스케일)
    if pd.notna(row.get('instagram_followers')) and row['instagram_followers'] > 0:
        instagram_score = min(100, (row['instagram_followers'] / 10000000) * 100)  # 1000만 = 100점, 최대 100점
        score += instagram_score * 0.25
    
    # Twitter 팔로워 - 20% 가중치 (선형 스케일)
    if pd.notna(row.get('twitter_followers')) and row['twitter_followers'] > 0:
        twitter_score = min(100, (row['twitter_followers'] / 10000000) * 100)  # 1000만 = 100점, 최대 100점
        score += twitter_score * 0.20
    
    # Spotify 팔로워 - 25% 가중치 (선형 스케일)
    if pd.notna(row.get('spotify_followers')) and row['spotify_followers'] > 0:
        spotify_score = min(100, (row['spotify_followers'] / 10000000) * 100)  # 1000만 = 100점, 최대 100점
        score += spotify_score * 0.25
    
    # 최종 점수를 0-100 스케일로 정규화
    # 이론적 최대값: 100*0.3 + 100*0.25 + 100*0.20 + 100*0.25 = 100
    # 실제로는 각 플랫폼에서 100점을 넘을 수 있으므로 100으로 제한
    normalized_score = min(100, score)
    
    return round(normalized_score, 2)