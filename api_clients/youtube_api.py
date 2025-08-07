"""
YouTube Data API v3 클라이언트
"""
import os
import re
import pandas as pd
import requests
from typing import List, Dict, Optional
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    print("python-dotenv가 설치되지 않았습니다. pip install python-dotenv")



class YouTubeAPIClient:
    """YouTube Data API v3 클라이언트"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API 키가 필요합니다. 환경변수 YOUTUBE_API_KEY를 설정하세요.")
            
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.session = requests.Session()
        
    
    def extract_channel_id_from_url(self, youtube_url: str) -> Optional[str]:
        """YouTube URL에서 채널 ID 추출"""
        
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
        """채널 통계 정보 조회"""
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
                'subscriber_count': int(subscriber_count) if subscriber_count and subscriber_count.isdigit() else 0,
                'hidden_subscriber_count': hidden_subscriber_count,
                'view_count': int(stats.get('viewCount', 0)) if stats.get('viewCount', '0').isdigit() else 0,
                'video_count': int(stats.get('videoCount', 0)) if stats.get('videoCount', '0').isdigit() else 0,
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
    
    def get_channels_from_url_list(self, url_artist_pairs: List[tuple]) -> pd.DataFrame:
        """YouTube URL 리스트로 채널 데이터 수집"""
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