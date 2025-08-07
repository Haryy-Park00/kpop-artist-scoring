"""
실시간 데이터 수집 컴포넌트
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.logging_config import get_project_logger
from utils.scoring import calculate_artist_score

logger = get_project_logger(__name__)


def collect_sns_links_for_single_artist(artist_name: str) -> dict:
    """단일 아티스트의 SNS 링크 수집 - 실제 크롤링"""
    try:
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


def collect_spotify_data(artist_name: str) -> dict:
    """Spotify 데이터 수집"""
    spotify_data = {
        'followers': 0,
        'popularity': 0,
        'spotify_url': None,
        'artist_name': artist_name
    }
    
    try:
        from api_clients.spotify_api import SpotifyAPIClient
        
        spotify_client = SpotifyAPIClient()
        spotify_results = spotify_client.search_artist(artist_name)
        
        if spotify_results:
            best_match = spotify_results[0]
            spotify_data.update({
                'followers': best_match['followers'],
                'popularity': best_match['popularity'],
                'spotify_url': best_match['spotify_url'],
                'artist_name': best_match['artist_name']
            })
            st.success(f"✅ Spotify: {best_match['artist_name']} ({best_match['followers']:,} 팔로워)")
        else:
            st.warning("❌ Spotify에서 아티스트를 찾을 수 없습니다.")
            
    except Exception as e:
        st.error(f"Spotify 검색 오류: {str(e)}")
    
    return spotify_data


def collect_artist_data_realtime(artist_name: str) -> dict:
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
            spotify_data = collect_spotify_data(artist_name)
            collected_data.update({
                'spotify': spotify_data['followers'],
                'popularity': spotify_data['popularity'],
                'spotify_url': spotify_data['spotify_url']
            })
        
        # 2. SNS 링크 수집 
        with st.spinner("🔍 SNS 링크 검색 중..."):
            try:
                sns_data = collect_sns_links_for_single_artist(artist_name)
                if sns_data:
                    collected_data.update({
                        'instagram_link': sns_data.get('instagram_link'),
                        'youtube_link': sns_data.get('youtube_link'),
                        'twitter_link': sns_data.get('twitter_link')
                    })
                else:
                    st.warning("❌ SNS 크롤링에 실패했습니다.")
                    
            except Exception as e:
                st.error(f"SNS 링크 수집 중 오류: {str(e)}")
        
        # 3. 자동 점수 계산
        if collected_data['spotify'] > 0 or collected_data['popularity'] > 0:
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