"""
차트 생성 컴포넌트
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.logging_config import get_project_logger

logger = get_project_logger(__name__)


def create_growth_metrics(youtube_df: pd.DataFrame, spotify_df: pd.DataFrame):
    """성장 지표 메트릭 카드 생성"""
    col1, col2, col3, col4 = st.columns(4)
    
    if youtube_df is not None and not youtube_df.empty:
        total_subscribers = youtube_df['subscriber_count'].sum()
        avg_subscribers = youtube_df['subscriber_count'].mean()
        
        with col1:
            st.metric(
                label="총 구독자 수",
                value=f"{total_subscribers:,.0f}명",
                delta=None
            )
        
        with col2:
            st.metric(
                label="평균 구독자 수",
                value=f"{avg_subscribers:,.0f}명",
                delta=None
            )
    
    if spotify_df is not None and not spotify_df.empty:
        avg_popularity = spotify_df['popularity'].mean()
        total_followers = spotify_df['followers'].sum()
        
        with col3:
            st.metric(
                label="Spotify 평균 인기도",
                value=f"{avg_popularity:.1f}/100",
                delta=None
            )
        
        with col4:
            st.metric(
                label="Spotify 총 팔로워",
                value=f"{total_followers:,.0f}명",
                delta=None
            )


def create_comparison_chart(integrated_df: pd.DataFrame):
    """플랫폼별 비교 차트 생성"""
    if integrated_df is None or integrated_df.empty:
        return None
    
    # YouTube와 Spotify 데이터가 모두 있는 아티스트만
    comparison_df = integrated_df.dropna(subset=['youtube_subscribers', 'spotify_followers'])
    
    if comparison_df.empty:
        return None
    
    fig = px.scatter(
        comparison_df,
        x='youtube_subscribers',
        y='spotify_followers',
        hover_name='artist_name',
        title='YouTube vs Spotify 팔로워 상관관계',
        labels={
            'youtube_subscribers': 'YouTube 구독자 수',
            'spotify_followers': 'Spotify 팔로워 수'
        },
        size='spotify_popularity',
        color='spotify_popularity',
        color_continuous_scale='viridis'
    )
    
    fig.update_layout(height=500)
    return fig


def create_subscriber_chart(youtube_df: pd.DataFrame):
    """YouTube 구독자 차트 생성"""
    if youtube_df is None or youtube_df.empty:
        return None
    
    # 상위 20명만 표시
    top_artists = youtube_df.nlargest(20, 'subscriber_count')
    
    fig = px.bar(
        top_artists,
        x='subscriber_count',
        y='artist_name',
        orientation='h',
        title='YouTube 구독자 수 Top 20',
        labels={'subscriber_count': '구독자 수', 'artist_name': '아티스트'},
        color='subscriber_count',
        color_continuous_scale='Blues'
    )
    
    fig.update_layout(
        height=600,
        yaxis={'categoryorder': 'total ascending'}
    )
    
    return fig


def create_ranking_chart(df: pd.DataFrame, score_column: str, title: str, height: int = 600):
    """랭킹 차트 생성"""
    if df is None or df.empty:
        return None
    
    # 상위 20명
    top_df = df.nlargest(20, score_column)
    
    fig = px.bar(
        top_df,
        x=score_column,
        y='artist',
        orientation='h',
        title=title,
        labels={score_column: '스코어', 'artist': '아티스트'},
        color=score_column,
        color_continuous_scale='RdYlGn'
    )
    
    fig.update_layout(
        height=height,
        yaxis={'categoryorder': 'total ascending'}
    )
    
    fig.update_traces(
        texttemplate='%{x:.1f}',
        textposition='outside'
    )
    
    return fig


def create_trend_chart(trends_df: pd.DataFrame, chart_type: str = 'gainers'):
    """트렌드 차트 생성 (상승자/하락자)"""
    if trends_df is None or trends_df.empty:
        return None
    
    if chart_type == 'gainers':
        filtered_df = trends_df[trends_df['change_rate'] > 0].nlargest(10, 'change_rate')
        title = '상위 상승자 Top 10'
        color_scale = 'Greens'
    else:  # losers
        filtered_df = trends_df[trends_df['change_rate'] < 0].nsmallest(10, 'change_rate')
        title = '상위 하락자 Top 10'
        color_scale = 'Reds'
    
    if filtered_df.empty:
        return None
    
    fig = px.bar(
        filtered_df,
        x='change_rate',
        y='artist',
        orientation='h',
        title=title,
        labels={'change_rate': '변화율 (%)', 'artist': '아티스트'},
        color='change_rate',
        color_continuous_scale=color_scale
    )
    
    category_order = 'total ascending' if chart_type == 'gainers' else 'total descending'
    fig.update_layout(height=400, yaxis={'categoryorder': category_order})
    
    return fig


def create_distribution_chart(trends_df: pd.DataFrame):
    """변화율 분포 차트 생성"""
    if trends_df is None or trends_df.empty:
        return None
    
    latest_week = trends_df['current_week'].max()
    latest_trends = trends_df[trends_df['current_week'] == latest_week]
    
    if latest_trends.empty:
        return None
    
    fig = px.histogram(
        latest_trends,
        x='change_rate',
        nbins=20,
        title='아티스트 변화율 분포',
        labels={'change_rate': '변화율 (%)', 'count': '아티스트 수'}
    )
    
    fig.add_vline(x=0, line_dash="dash", line_color="red", 
                  annotation_text="변화 없음")
    
    return fig


def create_category_scores_chart(category_df: pd.DataFrame):
    """카테고리별 점수 차트 생성"""
    if category_df is None or category_df.empty:
        return None
    
    fig = px.bar(
        category_df,
        x="카테고리",
        y="점수",
        title="카테고리별 점수",
        color="점수",
        color_continuous_scale="RdYlGn",
        range_color=[1, 10]
    )
    
    fig.update_layout(height=400)
    return fig


def create_correlation_chart(history_df: pd.DataFrame):
    """자동 점수 vs 수동 점수 상관관계 차트"""
    if history_df is None or len(history_df) <= 1:
        return None
    
    # 문자열을 숫자로 변환
    history_df['자동점수_num'] = pd.to_numeric(history_df['자동점수'], errors='coerce')
    history_df['수동점수_num'] = pd.to_numeric(history_df['수동점수'], errors='coerce')
    
    fig = px.scatter(
        history_df,
        x='자동점수_num',
        y='수동점수_num',
        hover_name='아티스트',
        title='자동 점수 vs 수동 점수 비교',
        labels={'자동점수_num': '자동 스코어', '수동점수_num': '수동 평가 점수'}
    )
    
    # 대각선 추가 (완벽한 일치선)
    fig.add_shape(
        type="line",
        x0=0, y0=0, x1=100, y1=100,
        line=dict(color="red", width=2, dash="dash"),
    )
    
    fig.update_layout(height=500)
    return fig