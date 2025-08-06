"""
YouTube Data API v3 클라이언트
"""
import os
import pandas as pd
import requests
from typing import List, Dict, Optional
import sys
import os
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    print("python-dotenv가 설치되지 않았습니다. pip install python-dotenv")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.common_functions import get_current_week_info, save_dataframe_csv
from utils.path_utils import get_path


class YouTubeAPIClient:
    """YouTube Data API v3 클라이언트"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: YouTube Data API v3 키 (환경변수 YOUTUBE_API_KEY 사용 가능)
        """
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API 키가 필요합니다. 환경변수 YOUTUBE_API_KEY를 설정하세요.")
            
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.session = requests.Session()
        
    def search_channels(self, query: str, max_results: int = 10) -> List[Dict]:
        """채널 검색"""
        url = f"{self.base_url}/search"
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'channel',
            'maxResults': max_results,
            'key': self.api_key
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        channels = []
        for item in response.json().get('items', []):
            channels.append({
                'channel_id': item['id']['channelId'],
                'title': item['snippet']['title'],
                'description': item['snippet']['description'][:100],
                'thumbnail': item['snippet']['thumbnails']['default']['url']
            })
            
        return channels
    
    def extract_channel_id_from_url(self, youtube_url: str) -> Optional[str]:
        """YouTube URL에서 채널 ID 추출"""
        import re
        
        # URL 정규화
        youtube_url = youtube_url.replace('youtu.be/', 'youtube.com/').replace('m.youtube.com', 'youtube.com')
        
        # 직접 채널 ID 패턴
        channel_id_pattern = r'youtube\.com/channel/([a-zA-Z0-9_-]+)'
        match = re.search(channel_id_pattern, youtube_url)
        if match:
            return match.group(1)
        
        # 핸들 패턴 (@username)
        handle_pattern = r'youtube\.com/@([a-zA-Z0-9_.-]+)'
        match = re.search(handle_pattern, youtube_url)
        if match:
            handle = match.group(1)
            print(f"  핸들 감지: @{handle}, 채널 ID로 변환 시도...")
            return self.get_channel_id_by_handle(handle)
        
        # 커스텀 URL 패턴들
        custom_patterns = [
            r'youtube\.com/c/([a-zA-Z0-9_-]+)',           # /c/channelname
            r'youtube\.com/user/([a-zA-Z0-9_-]+)',        # /user/username
        ]
        
        for pattern in custom_patterns:
            match = re.search(pattern, youtube_url)
            if match:
                custom_name = match.group(1)
                print(f"  커스텀 URL 감지: {custom_name}, 채널 ID로 변환 시도...")
                return self.get_channel_id_by_username(custom_name)
                
        return None
    
    def get_channel_id_by_handle(self, handle: str) -> Optional[str]:
        """@핸들로 채널 ID 조회"""
        # YouTube Data API는 핸들을 직접 지원하지 않으므로 검색으로 대체
        return self.get_channel_id_by_username(handle)
    
    def get_channel_id_by_username(self, username: str) -> Optional[str]:
        """사용자명/핸들로 채널 ID 조회"""
        # @핸들 처리
        if username.startswith('@'):
            username = username[1:]
            
        url = f"{self.base_url}/search"
        params = {
            'part': 'snippet',
            'q': username,
            'type': 'channel',
            'maxResults': 5,  # 더 많은 결과를 가져와서 정확한 매치 찾기
            'key': self.api_key
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        items = response.json().get('items', [])
        
        # 정확한 매치 우선 찾기
        for item in items:
            title = item['snippet']['title'].lower()
            if username.lower() in title or title in username.lower():
                return item['id']['channelId']
        
        # 정확한 매치가 없으면 첫 번째 결과 반환
        if items:
            return items[0]['id']['channelId']
            
        return None

    def get_channel_statistics(self, channel_ids: List[str]) -> List[Dict]:
        """채널 통계 정보 조회 (최대 50개 동시 조회)"""
        if len(channel_ids) > 50:
            raise ValueError("한 번에 최대 50개 채널만 조회 가능합니다.")
            
        url = f"{self.base_url}/channels"
        params = {
            'part': 'statistics,snippet',
            'id': ','.join(channel_ids),
            'key': self.api_key
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        results = []
        for item in response.json().get('items', []):
            stats = item.get('statistics', {})
            snippet = item.get('snippet', {})
            
            # 구독자 수가 숨겨진 경우 처리
            subscriber_count = stats.get('subscriberCount')
            hidden_subscriber_count = stats.get('hiddenSubscriberCount', False)
            
            results.append({
                'channel_id': item['id'],
                'channel_title': snippet.get('title', ''),
                'subscriber_count': int(subscriber_count) if subscriber_count else None,
                'hidden_subscriber_count': hidden_subscriber_count,
                'view_count': int(stats.get('viewCount', 0)),
                'video_count': int(stats.get('videoCount', 0)),
                'description': snippet.get('description', '')[:200],
                'published_at': snippet.get('publishedAt', ''),
                'country': snippet.get('country', ''),
                'custom_url': snippet.get('customUrl', '')
            })
            
        return results
    
    def get_channel_data_from_url(self, youtube_url: str, artist_name: str = None) -> Dict:
        """YouTube URL로 직접 채널 데이터 조회"""
        channel_id = self.extract_channel_id_from_url(youtube_url)
        
        if not channel_id:
            raise ValueError(f"YouTube URL에서 채널 ID를 추출할 수 없습니다: {youtube_url}")
        
        statistics = self.get_channel_statistics([channel_id])
        
        if not statistics:
            raise ValueError(f"채널 정보를 가져올 수 없습니다: {channel_id}")
        
        channel_data = statistics[0]
        if artist_name:
            channel_data['artist_name'] = artist_name
            
        return channel_data
    
    def get_artist_channels(self, artist_names: List[str]) -> pd.DataFrame:
        """아티스트명으로 채널 검색 및 통계 수집"""
        all_data = []
        
        for artist in artist_names:
            print(f"검색 중: {artist}")
            
            try:
                # 채널 검색
                search_results = self.search_channels(f"{artist} official", max_results=3)
                
                if not search_results:
                    print(f"  - 채널을 찾을 수 없습니다: {artist}")
                    continue
                
                # 통계 정보 조회
                channel_ids = [ch['channel_id'] for ch in search_results]
                statistics = self.get_channel_statistics(channel_ids)
                
                # 가장 구독자 수가 많은 채널 선택
                best_channel = max(statistics, 
                                 key=lambda x: x['subscriber_count'] or 0)
                
                best_channel['artist_name'] = artist
                all_data.append(best_channel)
                
                print(f"  - 채널 발견: {best_channel['channel_title']}")
                print(f"  - 구독자 수: {best_channel['subscriber_count']:,}" if best_channel['subscriber_count'] else "  - 구독자 수: 비공개")
                
            except Exception as e:
                print(f"  - 오류 발생 ({artist}): {e}")
                continue
                
        return pd.DataFrame(all_data)
    
    def get_channels_from_url_list(self, url_artist_pairs: List[tuple]) -> pd.DataFrame:
        """YouTube URL 리스트로 직접 채널 데이터 수집
        
        Args:
            url_artist_pairs: [(youtube_url, artist_name), ...] 형태의 리스트
            
        Returns:
            pd.DataFrame: 채널 데이터
        """
        all_data = []
        
        for youtube_url, artist_name in url_artist_pairs:
            print(f"수집 중: {artist_name} - {youtube_url}")
            
            try:
                channel_data = self.get_channel_data_from_url(youtube_url, artist_name)
                all_data.append(channel_data)
                
                print(f"  ✅ 성공: {channel_data['channel_title']}")
                print(f"  - 구독자 수: {channel_data['subscriber_count']:,}" if channel_data['subscriber_count'] else "  - 구독자 수: 비공개")
                
            except Exception as e:
                print(f"  ❌ 실패 ({artist_name}): {e}")
                continue
                
        return pd.DataFrame(all_data)
    
    def save_artist_youtube_data(self, artist_list_file: str = None) -> str:
        """아티스트 리스트 파일에서 YouTube 데이터 수집 및 저장"""
        # 아티스트 리스트 로드
        if not artist_list_file:
            artist_folder = get_path("data/artist_list")
            import glob
            files = glob.glob(str(artist_folder / "*한터차트*월드*.csv"))
            if not files:
                raise FileNotFoundError("아티스트 리스트 파일을 찾을 수 없습니다.")
            artist_list_file = max(files)  # 가장 최신 파일
            
        print(f"아티스트 리스트 로드: {artist_list_file}")
        artist_df = pd.read_csv(artist_list_file)
        
        if '아티스트명' not in artist_df.columns:
            raise ValueError("'아티스트명' 컬럼을 찾을 수 없습니다.")
            
        artist_names = artist_df['아티스트명'].unique().tolist()
        print(f"총 {len(artist_names)}명의 아티스트 YouTube 데이터 수집 시작")
        
        # YouTube 데이터 수집
        youtube_df = self.get_artist_channels(artist_names)
        
        # 원본 아티스트 데이터와 병합
        merged_df = artist_df.merge(
            youtube_df[['artist_name', 'channel_title', 'subscriber_count', 'view_count', 'video_count']],
            left_on='아티스트명',
            right_on='artist_name',
            how='left'
        )
        
        # 저장
        year, week_number, _ = get_current_week_info()
        output_path = get_path(f"data/follower/{year}년_{week_number}주차_YouTube_구독자.csv")
        save_dataframe_csv(youtube_df, output_path)
        
        # 통합 데이터도 저장
        integrated_path = get_path(f"data/integrated_social/{year}년_{week_number}주차_아티스트_YouTube_통합.csv")
        integrated_path.parent.mkdir(exist_ok=True)
        save_dataframe_csv(merged_df, integrated_path)
        
        print(f"YouTube 데이터 저장 완료: {output_path}")
        print(f"통합 데이터 저장 완료: {integrated_path}")
        
        return str(output_path)


def main():
    """테스트 실행"""
    # API 키 확인
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("환경변수 YOUTUBE_API_KEY를 설정해주세요.")
        print("예: export YOUTUBE_API_KEY='your_api_key_here'")
        return
        
    client = YouTubeAPIClient(api_key)
    
    # 테스트 아티스트들
    test_artists = ["BTS", "BLACKPINK", "NewJeans", "IVE", "aespa"]
    
    print("=== YouTube API 테스트 ===")
    youtube_df = client.get_artist_channels(test_artists)
    print(youtube_df[['artist_name', 'channel_title', 'subscriber_count']])
    

if __name__ == "__main__":
    main()