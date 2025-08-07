#!/usr/bin/env python3
"""
아티스트 데이터 대시보드
Streamlit을 사용한 실시간 데이터 시각화
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import glob
import os
import json
from pathlib import Path
import sys
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from utils.path_utils import get_path
from utils.common_functions import get_current_week_info
from utils.scoring import calculate_artist_score
from analytics.weekly_score_tracker import WeeklyScoreTracker

# 페이지 설정
st.set_page_config(
    page_title="K-Pop 아티스트 데이터 대시보드",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)


def collect_sns_links_for_single_artist(artist_name):
    """단일 아티스트의 SNS 링크 수집 - 실제 크롤링"""
    try:
        # 실제 SNS 크롤링 함수 임포트 및 호출
        from crawlers.sns_link_collector import collect_single_artist_sns_links
        
        # 검색 시작 알림
        progress_placeholder = st.empty()
        progress_placeholder.info(f"🔍 {artist_name}의 SNS 링크를 네이버에서 검색 중...")
        
        sns_data = collect_single_artist_sns_links(artist_name)
        
        if sns_data:
            # 개별 링크 발견 상태 표시
            links_found = []
            if sns_data.get('instagram_link'):
                links_found.append("📸 Instagram")
            if sns_data.get('youtube_link'):
                links_found.append("🎵 YouTube")  
            if sns_data.get('twitter_link'):
                links_found.append("🐦 Twitter")
            
            if links_found:
                progress_placeholder.success(f"✅ 발견된 링크: {', '.join(links_found)}")
            else:
                progress_placeholder.warning("❌ 검색 완료되었지만 SNS 링크를 찾을 수 없습니다.")
            
            return sns_data
        else:
            progress_placeholder.error("❌ SNS 링크 검색에 실패했습니다. Chrome 드라이버 설정을 확인해주세요.")
            return None
        
    except ImportError as e:
        st.error(f"❌ SNS 크롤링 모듈 임포트 오류: {e}")
        st.info("💡 crawlers/sns_link_collector.py 파일이 존재하는지 확인해주세요.")
        return None
    except Exception as e:
        st.error(f"❌ SNS 링크 수집 중 예상치 못한 오류 발생: {e}")
        st.info("💡 Chrome 브라우저와 ChromeDriver가 설치되어 있는지 확인해주세요.")
        return None


@st.cache_data(ttl=3600)  # 1시간 캐시
def load_latest_data():
    try:
        # YouTube 데이터
        youtube_files = glob.glob(str(get_path("data/follower/*YouTube*.csv")))
        youtube_df = None
        if youtube_files:
            latest_youtube = max(youtube_files)
            youtube_df = pd.read_csv(latest_youtube)
            youtube_df['data_source'] = 'YouTube'
        
        # Spotify 데이터
        spotify_files = glob.glob(str(get_path("data/follower/*Spotify*.csv")))
        spotify_df = None
        if spotify_files:
            latest_spotify = max(spotify_files)
            spotify_df = pd.read_csv(latest_spotify)
            spotify_df['data_source'] = 'Spotify'
        
        # 아티스트 리스트
        artist_files = glob.glob(str(get_path("data/artist_list/*한터차트*월드*.csv")))
        artist_df = None
        if artist_files:
            latest_artist = max(artist_files)
            artist_df = pd.read_csv(latest_artist)
        
        # BigC 아티스트 데이터 (SNS + Spotify 통합)
        bigc_files = glob.glob(str(get_path("data/bigc_pipeline/*빅크*SNS팔로워*.csv")))
        bigc_df = None
        if bigc_files:
            latest_bigc = max(bigc_files)
            bigc_df = pd.read_csv(latest_bigc)
        
        return youtube_df, spotify_df, integrated_df, artist_df, bigc_df
        
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return None, None, None, None, None


def create_growth_metrics(youtube_df, spotify_df):
    """성장 지표 메트릭 카드"""
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


def create_bigc_artist_scoring_dashboard(bigc_df):
    """BigC 아티스트 스코어링 대시보드"""
    if bigc_df is None or bigc_df.empty:
        st.warning("BigC 아티스트 데이터가 없습니다.")
        return
    
    # 데이터 전처리
    df = bigc_df.copy()
    
    # 스코어 계산
    df['total_score'] = df.apply(calculate_artist_score, axis=1)
    
    # 데이터가 있는 아티스트만 필터링
    valid_df = df[df['total_score'] > 0].copy()
    
    if valid_df.empty:
        st.warning("스코어를 계산할 수 있는 아티스트가 없습니다.")
        return
    
    # 상위 20명 아티스트 랭킹
    top_artists = valid_df.nlargest(20, 'total_score')
    
    st.subheader("🏆 아티스트 종합 스코어 랭킹 Top 20")
    
    # 랭킹 차트
    fig_ranking = px.bar(
        top_artists,
        x='total_score',
        y='artist',
        orientation='h',
        title='아티스트 종합 스코어 랭킹',
        labels={'total_score': '종합 스코어', 'artist': '아티스트'},
        color='total_score',
        color_continuous_scale='RdYlGn'
    )
    
    fig_ranking.update_layout(
        height=600,
        yaxis={'categoryorder': 'total ascending'}
    )
    
    fig_ranking.update_traces(
        texttemplate='%{x:.1f}',
        textposition='outside'
    )
    
    st.plotly_chart(fig_ranking, use_container_width=True)
    
    # 주간 트렌드 추가 (스코어링과 함께 표시)
    try:
        st.subheader("📈 주간 변화율 분석")
        
        tracker = WeeklyScoreTracker()
        trends_df = tracker.generate_weekly_trends()
        
        if trends_df is not None and not trends_df.empty:
            # 상위 상승자/하락자
            top_gainers, top_losers = tracker.get_top_gainers_losers(trends_df, top_n=10)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔥 이번 주 상위 상승자")
                if top_gainers is not None and not top_gainers.empty:
                    fig_gainers = px.bar(
                        top_gainers.head(10),
                        x='change_rate',
                        y='artist',
                        orientation='h',
                        title='상위 상승자 Top 10',
                        labels={'change_rate': '변화율 (%)', 'artist': '아티스트'},
                        color='change_rate',
                        color_continuous_scale='Greens'
                    )
                    fig_gainers.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_gainers, use_container_width=True)
                else:
                    st.info("상승자 데이터가 없습니다.")
            
            with col2:
                st.subheader("📉 이번 주 상위 하락자")
                if top_losers is not None and not top_losers.empty:
                    fig_losers = px.bar(
                        top_losers.head(10),
                        x='change_rate',
                        y='artist',
                        orientation='h',
                        title='상위 하락자 Top 10',
                        labels={'change_rate': '변화율 (%)', 'artist': '아티스트'},
                        color='change_rate',
                        color_continuous_scale='Reds'
                    )
                    fig_losers.update_layout(height=400, yaxis={'categoryorder': 'total descending'})
                    st.plotly_chart(fig_losers, use_container_width=True)
                else:
                    st.info("하락자 데이터가 없습니다.")
            
            # 주간 요약
            summary = tracker.generate_weekly_summary(trends_df)
            if summary:
                st.subheader(f"📊 {summary['week']} 주간 요약")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("전체 아티스트", f"{summary['total_artists']}명")
                with col2:
                    st.metric("상승", f"{summary['artists_up']}명", delta="📈")
                with col3:
                    st.metric("하락", f"{summary['artists_down']}명", delta="📉")
                with col4:
                    st.metric("유지", f"{summary['artists_stable']}명", delta="➖")
        else:
            st.info("주간 비교 데이터가 부족합니다. 최소 2주간의 데이터가 필요합니다.")
    
    except Exception as e:
        st.warning(f"주간 트렌드 로드 중 오류: {e}")
    
    # 상세 테이블 (트렌드 정보 포함)
    st.subheader("📋 아티스트별 상세 스코어 & 트렌드")
    
    # 트렌드 데이터와 합치기
    try:
        if trends_df is not None and not trends_df.empty:
            # 최신 주간 트렌드 데이터
            latest_week = trends_df['current_week'].max()
            latest_trends = trends_df[trends_df['current_week'] == latest_week].copy()
            
            # 스코어 데이터와 트렌드 데이터 병합
            merged_df = valid_df.merge(
                latest_trends[['artist', 'change_rate', 'trend', 'previous_score']], 
                on='artist', 
                how='left'
            )
            
            display_columns = [
                'artist', 'entertainment', 'total_score', 'previous_score', 'change_rate', 'trend',
                'popularity', 'instagram_followers', 'twitter_followers', 'spotify_followers'
            ]
            
            display_df = merged_df[display_columns].copy()
            display_df.columns = [
                '아티스트', '소속사', '현재스코어', '이전스코어', '변화율(%)', '트렌드',
                'Spotify인기도', 'Instagram팔로워', 'Twitter팔로워', 'Spotify팔로워'
            ]
            
            # 트렌드에 이모지 추가
            trend_emoji = {'up': '📈', 'down': '📉', 'stable': '➖'}
            display_df['트렌드'] = display_df['트렌드'].map(trend_emoji).fillna('➖')
            
            # 정렬 옵션 확장
            sort_options = ["현재스코어", "변화율(%)", "Spotify인기도", "Instagram팔로워", "Twitter팔로워", "Spotify팔로워"]
        else:
            # 트렌드 데이터가 없을 때
            display_columns = [
                'artist', 'entertainment', 'total_score', 'popularity',
                'instagram_followers', 'twitter_followers', 'spotify_followers'
            ]
            
            display_df = valid_df[display_columns].copy()
            display_df.columns = [
                '아티스트', '소속사', '현재스코어', 'Spotify인기도',
                'Instagram팔로워', 'Twitter팔로워', 'Spotify팔로워'
            ]
            
            sort_options = ["현재스코어", "Spotify인기도", "Instagram팔로워", "Twitter팔로워", "Spotify팔로워"]
    
    except:
        # 오류 시 기본 테이블
        display_columns = [
            'artist', 'entertainment', 'total_score', 'popularity',
            'instagram_followers', 'twitter_followers', 'spotify_followers'
        ]
        
        display_df = valid_df[display_columns].copy()
        display_df.columns = [
            '아티스트', '소속사', '현재스코어', 'Spotify인기도',
            'Instagram팔로워', 'Twitter팔로워', 'Spotify팔로워'
        ]
        
        sort_options = ["현재스코어", "Spotify인기도", "Instagram팔로워", "Twitter팔로워", "Spotify팔로워"]
    
    # 정렬 옵션
    sort_option = st.selectbox("정렬 기준", sort_options)
    display_df_sorted = display_df.sort_values(sort_option, ascending=False)
    
    st.dataframe(
        display_df_sorted,
        use_container_width=True,
        height=400
    )
    
    # CSV 다운로드
    csv = display_df_sorted.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="아티스트 스코어 & 트렌드 CSV 다운로드",
        data=csv,
        file_name=f"BigC_아티스트_스코어_트렌드_{get_current_week_info()[0]}년_{get_current_week_info()[1]}주차.csv",
        mime="text/csv"
    )

def collect_artist_data_realtime(artist_name):
    """실시간 아티스트 데이터 수집"""
    collected_data = {
        'name': artist_name,
        'entertainment': 'N/A',
        'auto_score': 0,
        'instagram': 0,
        'twitter': 0,
        'spotify': 0,
        'popularity': 0,
        'instagram_link': None,
        'youtube_link': None,
        'twitter_link': None,
        'spotify_url': None
    }
    
    try:
        # 1. Spotify 데이터 수집
        with st.spinner("🎵 Spotify 데이터 검색 중..."):
            try:
                from api_clients.spotify_api import SpotifyAPIClient
                spotify_client = SpotifyAPIClient()
                spotify_results = spotify_client.search_artist(artist_name)
                
                if spotify_results:
                    best_match = spotify_results[0]
                    collected_data['spotify'] = best_match['followers']
                    collected_data['popularity'] = best_match['popularity']
                    collected_data['spotify_url'] = best_match['spotify_url']
                    st.success(f"✅ Spotify: {best_match['artist_name']} ({best_match['followers']:,} 팔로워)")
                else:
                    st.warning("❌ Spotify에서 아티스트를 찾을 수 없습니다.")
            except Exception as e:
                st.error(f"Spotify 검색 오류: {str(e)}")
        
        # 2. SNS 링크 수집 (셀레니움 기반)
        with st.spinner("🔍 SNS 링크 검색 중..."):
            try:
                # 실제 SNS 크롤링 함수 호출
                sns_data = collect_sns_links_for_single_artist(artist_name)
                if sns_data:
                    collected_data['instagram_link'] = sns_data.get('instagram_link')
                    collected_data['youtube_link'] = sns_data.get('youtube_link')
                    collected_data['twitter_link'] = sns_data.get('twitter_link')
                    
                    # 발견된 링크들에 대한 개별 피드백은 collect_sns_links_for_single_artist에서 처리됨
                else:
                    st.warning("❌ SNS 크롤링에 실패했습니다.")
                    
            except Exception as e:
                st.error(f"SNS 링크 수집 중 오류: {str(e)}")
        
        # 3. 자동 점수 계산
        if collected_data['spotify'] > 0 or collected_data['popularity'] > 0:
            # 임시 데이터프레임 행 생성
            temp_row = pd.Series({
                'popularity': collected_data['popularity'],
                'instagram_followers': collected_data['instagram'],
                'twitter_followers': collected_data['twitter'],
                'spotify_followers': collected_data['spotify']
            })
            collected_data['auto_score'] = calculate_artist_score(temp_row)
        
        return collected_data
        
    except Exception as e:
        st.error(f"데이터 수집 중 오류 발생: {str(e)}")
        return collected_data


def create_manual_scoring_dashboard(bigc_df):
    """수동 아티스트 점수 매기기 대시보드"""
    
    # 세션 스테이트 초기화
    if 'manual_scores' not in st.session_state:
        st.session_state.manual_scores = {}
    
    st.subheader("🎯 아티스트 선택")
    
    # 아티스트 선택 방법
    selection_method = st.radio(
        "아티스트 선택 방법",
        ["기존 아티스트에서 선택", "새 아티스트 검색"],
        horizontal=True
    )
    
    selected_artist = None
    artist_info = {}
    
    if selection_method == "기존 아티스트에서 선택":
        if bigc_df is not None and not bigc_df.empty:
            artists_list = sorted(bigc_df['artist'].dropna().unique())
            selected_artist = st.selectbox("아티스트 선택", ["선택하세요..."] + artists_list)
            
            if selected_artist != "선택하세요...":
                artist_row = bigc_df[bigc_df['artist'] == selected_artist].iloc[0]
                artist_info = {
                    'name': selected_artist,
                    'entertainment': artist_row.get('entertainment', 'N/A'),
                    'auto_score': calculate_artist_score(artist_row),
                    'instagram': artist_row.get('instagram_followers', 0),
                    'twitter': artist_row.get('twitter_followers', 0),
                    'spotify': artist_row.get('spotify_followers', 0),
                    'popularity': artist_row.get('popularity', 0)
                }
        else:
            st.warning("BigC 아티스트 데이터를 불러올 수 없습니다.")
            return
    
    else:  # 새 아티스트 검색
        new_artist_name = st.text_input("아티스트 이름을 입력하세요")
        
        if new_artist_name:
            if st.button("🔍 실시간 데이터 수집", type="primary"):
                st.write("데이터 수집을 시작합니다...")
                artist_info = collect_artist_data_realtime(new_artist_name)
                selected_artist = new_artist_name
                st.session_state.collected_data = artist_info
                
            # 세션에서 수집된 데이터 사용
            elif 'collected_data' in st.session_state and st.session_state.collected_data['name'] == new_artist_name:
                artist_info = st.session_state.collected_data
                selected_artist = new_artist_name
    
    if selected_artist and selected_artist != "선택하세요...":
        # 아티스트 정보 표시
        st.markdown("---")
        st.subheader(f"📊 {artist_info['name']} 정보")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("소속사", artist_info['entertainment'])
        with col2:
            st.metric("자동 스코어", f"{artist_info['auto_score']:.1f}")
        with col3:
            st.metric("Spotify 팔로워", f"{artist_info['spotify']:,}")
        with col4:
            st.metric("Spotify 인기도", f"{artist_info['popularity']:.1f}")
        
        # SNS 링크 표시
        if any([artist_info.get('instagram_link'), artist_info.get('youtube_link'), artist_info.get('twitter_link'), artist_info.get('spotify_url')]):
            st.subheader("🔗 SNS 링크")
            link_cols = st.columns(4)
            
            with link_cols[0]:
                if artist_info.get('instagram_link'):
                    st.markdown(f"📸 [Instagram]({artist_info['instagram_link']})")
                else:
                    st.write("📸 Instagram: 없음")
            
            with link_cols[1]:
                if artist_info.get('youtube_link'):
                    st.markdown(f"🎵 [YouTube]({artist_info['youtube_link']})")
                else:
                    st.write("🎵 YouTube: 없음")
            
            with link_cols[2]:
                if artist_info.get('twitter_link'):
                    st.markdown(f"🐦 [Twitter]({artist_info['twitter_link']})")
                else:
                    st.write("🐦 Twitter: 없음")
            
            with link_cols[3]:
                if artist_info.get('spotify_url'):
                    st.markdown(f"🎵 [Spotify]({artist_info['spotify_url']})")
                else:
                    st.write("🎵 Spotify: 없음")
        
        # 점수 입력 섹션
        st.markdown("---")
        st.subheader("⭐ 점수 매기기")
        
        # 평가 카테고리 설정
        categories = {
            "음악성": {"weight": 25, "description": "작곡, 작사, 보컬, 랩 실력 등"},
            "퍼포먼스": {"weight": 25, "description": "무대 매너, 댄스, 라이브 실력 등"},
            "비주얼": {"weight": 20, "description": "외모, 스타일링, 카리스마 등"},
            "인기도": {"weight": 15, "description": "팬층, 화제성, 미디어 노출 등"},
            "성장 가능성": {"weight": 15, "description": "향후 발전 가능성, 트렌드 적응력 등"}
        }
        
        # 가중치 조정 (선택사항)
        with st.expander("🔧 가중치 조정 (기본값 사용 권장)"):
            st.write("각 카테고리의 중요도를 조정할 수 있습니다.")
            for category in categories:
                categories[category]["weight"] = st.slider(
                    f"{category} 가중치 (%)",
                    min_value=0,
                    max_value=50,
                    value=categories[category]["weight"],
                    step=5
                )
        
        # 점수 입력 폼
        scores = {}
        st.write("**각 항목을 1-10점으로 평가해주세요:**")
        
        for category, info in categories.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                scores[category] = st.slider(
                    f"{category} ({info['description']})",
                    min_value=1,
                    max_value=10,
                    value=5,
                    step=1,
                    key=f"score_{category}_{selected_artist}"
                )
            with col2:
                st.write(f"가중치: {info['weight']}%")
        
        # 종합 점수 계산
        total_weight = sum(cat["weight"] for cat in categories.values())
        if total_weight > 0:
            weighted_score = sum(scores[cat] * categories[cat]["weight"] for cat in scores) / total_weight
            final_score = (weighted_score / 10) * 100  # 100점 만점으로 변환
            
            st.markdown("---")
            st.subheader("🏆 평가 결과")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("종합 점수", f"{final_score:.1f}/100")
            with col2:
                st.metric("자동 스코어", f"{artist_info['auto_score']:.1f}/100")
            with col3:
                score_diff = final_score - artist_info['auto_score']
                st.metric("차이", f"{score_diff:+.1f}", delta=f"{score_diff:+.1f}")
            
            # 카테고리별 점수 시각화
            category_df = pd.DataFrame([
                {"카테고리": cat, "점수": scores[cat], "가중치": info["weight"]}
                for cat, info in categories.items()
            ])
            
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
            st.plotly_chart(fig, use_container_width=True)
            
            # 점수 저장
            if st.button("💾 점수 저장", type="primary"):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                score_data = {
                    'timestamp': timestamp,
                    'artist': artist_info['name'],
                    'entertainment': artist_info['entertainment'],
                    'manual_score': final_score,
                    'auto_score': artist_info['auto_score'],
                    'categories': scores,
                    'weights': {cat: info["weight"] for cat, info in categories.items()}
                }
                
                st.session_state.manual_scores[f"{selected_artist}_{timestamp}"] = score_data
                st.success(f"✅ {artist_info['name']}의 점수가 저장되었습니다!")
                st.balloons()
        
        else:
            st.error("가중치의 총합이 0입니다. 가중치를 조정해주세요.")
    
    # 저장된 점수 히스토리
    if st.session_state.manual_scores:
        st.markdown("---")
        st.subheader("📈 평가 히스토리")
        
        # 히스토리 데이터 변환
        history_data = []
        for key, data in st.session_state.manual_scores.items():
            history_data.append({
                '평가일시': data['timestamp'],
                '아티스트': data['artist'],
                '소속사': data['entertainment'],
                '수동점수': f"{data['manual_score']:.1f}",
                '자동점수': f"{data['auto_score']:.1f}",
                '차이': f"{data['manual_score'] - data['auto_score']:+.1f}"
            })
        
        history_df = pd.DataFrame(history_data)
        history_df = history_df.sort_values('평가일시', ascending=False)
        
        st.dataframe(history_df, use_container_width=True)
        
        # 히스토리 차트
        if len(history_data) > 1:
            fig = px.scatter(
                history_df,
                x='자동점수',
                y='수동점수',
                hover_name='아티스트',
                title='자동 점수 vs 수동 점수 비교',
                labels={'자동점수': '자동 스코어', '수동점수': '수동 평가 점수'}
            )
            
            # 대각선 추가 (완벽한 일치선)
            fig.add_shape(
                type="line",
                x0=0, y0=0, x1=100, y1=100,
                line=dict(color="red", width=2, dash="dash"),
            )
            
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        
        # 히스토리 초기화 버튼
        if st.button("🗑️ 히스토리 초기화"):
            st.session_state.manual_scores = {}
            st.rerun()


def create_weekly_trends_dashboard():
    """주간 트렌드 분석 대시보드"""
    st.subheader("📈 주간 트렌드 분석")
    
    try:
        # 주간 트렌드 데이터 로드
        tracker = WeeklyScoreTracker()
        trends_df = tracker.generate_weekly_trends()
        
        if trends_df is None or trends_df.empty:
            st.warning("주간 비교 데이터가 부족합니다. 최소 2주간의 데이터가 필요합니다.")
            st.info("매주 데이터를 수집하면 트렌드 분석이 가능합니다.")
            return
        
        # 최신 주간 요약
        summary = tracker.generate_weekly_summary(trends_df)
        if summary:
            st.subheader(f"📊 {summary['week']} 주간 요약")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("전체 아티스트", f"{summary['total_artists']}명")
            with col2:
                st.metric("상승", f"{summary['artists_up']}명", 
                         delta=f"+{summary['avg_change_rate']:.2f}%" if summary['avg_change_rate'] > 0 else None)
            with col3:
                st.metric("하락", f"{summary['artists_down']}명")
            with col4:
                st.metric("유지", f"{summary['artists_stable']}명")
        
        # 상위 상승자/하락자
        top_gainers, top_losers = tracker.get_top_gainers_losers(trends_df, top_n=10)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔥 이번 주 상위 상승자")
            if top_gainers is not None and not top_gainers.empty:
                fig_gainers = px.bar(
                    top_gainers.head(10),
                    x='change_rate',
                    y='artist',
                    orientation='h',
                    title='상위 상승자 Top 10',
                    labels={'change_rate': '변화율 (%)', 'artist': '아티스트'},
                    color='change_rate',
                    color_continuous_scale='Greens'
                )
                fig_gainers.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_gainers, use_container_width=True)
            else:
                st.info("상승자 데이터가 없습니다.")
        
        with col2:
            st.subheader("📉 이번 주 상위 하락자")
            if top_losers is not None and not top_losers.empty:
                fig_losers = px.bar(
                    top_losers.head(10),
                    x='change_rate',
                    y='artist',
                    orientation='h',
                    title='상위 하락자 Top 10',
                    labels={'change_rate': '변화율 (%)', 'artist': '아티스트'},
                    color='change_rate',
                    color_continuous_scale='Reds'
                )
                fig_losers.update_layout(height=400, yaxis={'categoryorder': 'total descending'})
                st.plotly_chart(fig_losers, use_container_width=True)
            else:
                st.info("하락자 데이터가 없습니다.")
        
        # 변화율 분포
        st.subheader("📊 변화율 분포")
        latest_week = trends_df['current_week'].max()
        latest_trends = trends_df[trends_df['current_week'] == latest_week].copy()
        
        if not latest_trends.empty:
            fig_dist = px.histogram(
                latest_trends,
                x='change_rate',
                nbins=20,
                title='아티스트 변화율 분포',
                labels={'change_rate': '변화율 (%)', 'count': '아티스트 수'}
            )
            fig_dist.add_vline(x=0, line_dash="dash", line_color="red", 
                              annotation_text="변화 없음")
            st.plotly_chart(fig_dist, use_container_width=True)
        
        # 상세 트렌드 테이블
        st.subheader("📋 상세 트렌드 데이터")
        
        if not latest_trends.empty:
            display_trends = latest_trends[[
                'artist', 'entertainment', 'current_score', 'previous_score', 
                'score_change', 'change_rate', 'trend'
            ]].copy()
            
            display_trends.columns = [
                '아티스트', '소속사', '현재스코어', '이전스코어', 
                '스코어변화', '변화율(%)', '트렌드'
            ]
            
            # 트렌드에 이모지 추가
            trend_emoji = {'up': '📈', 'down': '📉', 'stable': '➖'}
            display_trends['트렌드'] = display_trends['트렌드'].map(trend_emoji)
            
            # 변화율로 정렬
            display_trends_sorted = display_trends.sort_values('변화율(%)', ascending=False)
            
            st.dataframe(
                display_trends_sorted,
                use_container_width=True,
                height=400
            )
            
            # CSV 다운로드
            csv = display_trends_sorted.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="주간 트렌드 CSV 다운로드",
                data=csv,
                file_name=f"주간_트렌드_{latest_week}.csv",
                mime="text/csv"
            )
    
    except Exception as e:
        st.error(f"주간 트렌드 분석 중 오류 발생: {e}")

def show_data_table(df, title):
    """데이터 테이블 표시"""
    if df is None or df.empty:
        st.warning(f"{title} 데이터가 없습니다.")
        return
    
    st.subheader(title)
    
    # 검색 기능
    search_term = st.text_input(f"{title} 검색", key=f"search_{title}")
    
    if search_term:
        # 아티스트명으로 검색
        if 'artist_name' in df.columns:
            filtered_df = df[df['artist_name'].str.contains(search_term, case=False, na=False)]
        elif '아티스트명' in df.columns:
            filtered_df = df[df['아티스트명'].str.contains(search_term, case=False, na=False)]
        else:
            filtered_df = df
    else:
        filtered_df = df
    
    # 데이터 표시
    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=400
    )
    
    # 다운로드 버튼
    csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label=f"{title} CSV 다운로드",
        data=csv,
        file_name=f"{title}_{get_current_week_info()[0]}년_{get_current_week_info()[1]}주차.csv",
        mime="text/csv"
    )

def main():
    """메인 대시보드"""
    st.title("🎵 K-Pop 아티스트 데이터 대시보드")
    st.markdown("---")
    
    # 사이드바
    st.sidebar.title("📊 대시보드 메뉴")
    
    # 데이터 로드
    with st.spinner("데이터를 로드하는 중..."):
        youtube_df, spotify_df, integrated_df, artist_df, bigc_df = load_latest_data()
    
    # 데이터 새로고침 버튼
    if st.sidebar.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
    
    # 메뉴 선택
    menu = st.sidebar.selectbox(
        "페이지 선택",
        ["🏆 BigC 아티스트 스코어링 & 트렌드", "⭐ 수동 아티스트 평가", "📺 YouTube 분석", "🎵 Spotify 분석", "📋 데이터 테이블", "ℹ️ 정보"]
    )
    
    if menu == "🏆 BigC 아티스트 스코어링 & 트렌드":
        st.header("🏆 BigC 아티스트 스코어링 & 트렌드")
        create_bigc_artist_scoring_dashboard(bigc_df)
    
    elif menu == "⭐ 수동 아티스트 평가":
        st.header("⭐ 수동 아티스트 평가")
        create_manual_scoring_dashboard(bigc_df)
    
    elif menu == "📺 YouTube 분석":
        st.header("📺 YouTube 분석")
        
        if youtube_df is not None:
            # 상세 차트들
            subscriber_chart = create_subscriber_chart(youtube_df)
            if subscriber_chart:
                st.plotly_chart(subscriber_chart, use_container_width=True)
            
            # 추가 분석
            st.subheader("📊 상세 통계")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("총 아티스트 수", len(youtube_df))
            with col2:
                st.metric("최고 구독자 수", f"{youtube_df['subscriber_count'].max():,.0f}명")
            with col3:
                st.metric("중간값", f"{youtube_df['subscriber_count'].median():,.0f}명")
        else:
            st.warning("YouTube 데이터가 없습니다.")
    
    elif menu == "🎵 Spotify 분석":
        st.header("🎵 Spotify 분석")
        
        if spotify_df is not None:
            st.info("Spotify API 키를 설정하면 더 자세한 분석이 가능합니다.")
            show_data_table(spotify_df, "Spotify 데이터")
        else:
            st.warning("Spotify 데이터가 없습니다. API 키를 설정해주세요.")
    
    elif menu == "📋 데이터 테이블":
        st.header("📋 데이터 테이블")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["YouTube", "Spotify", "통합 데이터", "아티스트 리스트", "BigC 아티스트"])
        
        with tab1:
            show_data_table(youtube_df, "YouTube")
        
        with tab2:
            show_data_table(spotify_df, "Spotify")
        
        with tab3:
            show_data_table(integrated_df, "통합 데이터")
        
        with tab4:
            show_data_table(artist_df, "아티스트 리스트")
        
        with tab5:
            show_data_table(bigc_df, "BigC 아티스트")
    
    elif menu == "ℹ️ 정보":
        st.header("ℹ️ 대시보드 정보")
        
        st.markdown("""
        ### 🎯 대시보드 기능
        - **실시간 데이터 시각화**: 수집된 아티스트 데이터를 실시간으로 시각화
        - **다중 플랫폼 분석**: YouTube, Spotify 등 여러 플랫폼 데이터 통합 분석
        - **검색 및 필터링**: 원하는 아티스트 데이터를 쉽게 찾기
        - **데이터 다운로드**: 분석 결과를 CSV로 다운로드
        
        ### 📊 주요 지표
        - **YouTube**: 구독자 수, 조회수, 영상 수
        - **Spotify**: 인기도 점수, 팔로워 수, 장르 정보
        
        ### 🔄 데이터 업데이트
        - 매일 오전 9시 자동 수집 (Cron job 설정 시)
        - 수동 새로고침 버튼으로 즉시 업데이트 가능
        
        ### 📱 사용법
        1. 사이드바에서 원하는 페이지 선택
        2. 차트에서 데이터 포인트 호버로 상세 정보 확인
        3. 검색 기능으로 특정 아티스트 찾기
        4. CSV 다운로드로 데이터 저장
        """)
        
        # 시스템 상태
        st.subheader("🔧 시스템 상태")
        
        # API 키 상태
        api_status = {
            "YouTube API": bool(os.getenv('YOUTUBE_API_KEY')),
            "Spotify API": bool(os.getenv('SPOTIFY_CLIENT_ID')),
        }
        
        for api, status in api_status.items():
            icon = "✅" if status else "❌"
            st.write(f"{icon} {api}: {'설정됨' if status else '미설정'}")
        
        # 데이터 파일 상태
        st.subheader("📁 데이터 파일 상태")
        data_status = {
            "YouTube 데이터": youtube_df is not None,
            "Spotify 데이터": spotify_df is not None,
            "통합 데이터": integrated_df is not None,
            "아티스트 리스트": artist_df is not None,
            "BigC 아티스트 데이터": bigc_df is not None
        }
        
        for data_type, status in data_status.items():
            icon = "✅" if status else "❌"
            st.write(f"{icon} {data_type}: {'있음' if status else '없음'}")

if __name__ == "__main__":
    main()