"""
Spotify Web API 클라이언트
"""
import os
import base64
import requests
import pandas as pd
from typing import Dict, List
import sys
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    print(f"✅ .env 파일 로드됨: {env_path}")
except ImportError:
    print("❌ python-dotenv가 설치되지 않았습니다. pip install python-dotenv")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.common_functions import get_current_week_info, save_dataframe_csv
from utils.path_utils import get_path


class SpotifyAPIClient:
    """Spotify Web API 클라이언트"""
    
    def __init__(self):
        """Spotify API 클라이언트 초기화 (.env 파일에서 자동 로드)"""
        # 환경변수에서 직접 로드
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        print(f"클라이언트 ID 로드됨: {self.client_id is not None}")
        print(f"클라이언트 시크릿 로드됨: {self.client_secret is not None}")
        
        if not self.client_id or not self.client_secret:
            print("❌ Spotify API 키가 설정되지 않았습니다.")
            raise ValueError("Spotify API 자격증명이 필요합니다.")
            
        self.access_token = self._get_access_token()
        print("✅ Spotify API 클라이언트 초기화 완료")
        
    def _get_access_token(self) -> str:
        """Client Credentials Flow로 액세스 토큰 획득"""
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}
        
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        return response.json()["access_token"]
    
    def search_artist(self, artist_name: str) -> List[Dict]:
        """아티스트 검색"""
        url = "https://api.spotify.com/v1/search"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {
            "q": artist_name,
            "type": "artist",
            "limit": 10
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        artists = []
        for artist in response.json()["artists"]["items"]:
            artists.append({
                "artist_id": artist["id"],
                "artist_name": artist["name"],
                "popularity": artist["popularity"],
                "followers": artist["followers"]["total"],
                "genres": ", ".join(artist["genres"]),
                "spotify_url": artist["external_urls"]["spotify"]
            })
        return artists
    
    
    def get_artists_data(self, artist_list_file: str = None) -> pd.DataFrame:
        """아티스트 리스트 파일에서 Spotify 데이터 수집"""
        # 아티스트 리스트 로드
        if artist_list_file:
            artist_df = pd.read_csv(artist_list_file)
        else:
            artist_folder = get_path("data/artist_list")
            import glob
            import os
            files = glob.glob(str(artist_folder / "*한터차트*월드*.csv"))
            
            if not files:
                print("❌ 아티스트 리스트 파일을 찾을 수 없습니다.")
                return pd.DataFrame()
            
            # 파일 수정 시간을 기준으로 가장 최신 파일 선택
            latest_file = max(files, key=os.path.getmtime)
            print(f"📁 아티스트 리스트 로드: {latest_file}")
            
            # 파일 정보 출력
            import datetime
            file_time = datetime.datetime.fromtimestamp(os.path.getmtime(latest_file))
            print(f"   파일 수정 시간: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            artist_df = pd.read_csv(latest_file)
        
        if '아티스트명' not in artist_df.columns:
            print("아티스트명' 컬럼을 찾을 수 없습니다.")
            return pd.DataFrame()
        
        artist_names = artist_df['아티스트명'].unique().tolist()
        print(f"{len(artist_names)}명의 아티스트")
        
        all_data = []
        
        for artist_name in artist_names:
            print(f"수집 중: {artist_name}")
            
            try:
                # 아티스트 검색
                artists = self.search_artist(artist_name)
                
                if artists:
                    # 첫 번째 검색 결과 선택
                    best_match = artists[0]
                    best_match['original_name'] = artist_name
                    all_data.append(best_match)
                    
                    print(f"  ✅ 성공: {best_match['artist_name']} (팔로워: {best_match['followers']:,})")
                else:
                    # 검색 결과가 없으면 null 데이터 추가
                    null_data = {
                        'artist_id': None,
                        'artist_name': None,
                        'popularity': None,
                        'followers': None,
                        'genres': None,
                        'spotify_url': None,
                        'original_name': artist_name
                    }
                    all_data.append(null_data)
                    print(f"  ❌ 검색 결과 없음: {artist_name}")
                    
            except Exception as e:
                print(f"  ❌ 오류 ({artist_name}): {e}")
                continue
        
        return pd.DataFrame(all_data)
    
    def save_artists_data(self, artist_list_file: str = None) -> str:
        """아티스트 Spotify 데이터 수집 및 저장"""
        df = self.get_artists_data(artist_list_file)
        
        if df.empty:
            print("수집된 데이터가 없습니다.")
            return None
        
        # 파일 저장
        year, week_number, _ = get_current_week_info()
        
        # 파일명 생성
        filename = f"{year}년_{week_number}주차_Spotify데이터.csv"
        output_path = get_path("data/follower") / filename
        
        # 폴더 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 저장
        save_dataframe_csv(df, output_path)
        
        # Google Sheets 업로드 시도
        try:
            from utils.google_sheets_uploader import GoogleSheetsUploader
            
            uploader = GoogleSheetsUploader()
            if uploader.client:
                # 스프레드시트 제목 생성
                sheet_title = f"Spotify_{year}년_{week_number}주차_데이터"
                sheet_url = uploader.create_new_sheet(sheet_title, str(output_path))
                if sheet_url:
                    print(f"📊 Google Sheets 업로드 완료: {sheet_url}")
            else:
                print("⚠️ Google Sheets 업로드 건너뜀 (인증 정보 없음)")
        except ImportError:
            print("⚠️ Google Sheets 업로더를 사용하려면 'pip install gspread google-auth'를 실행하세요")
        except Exception as e:
            print(f"⚠️ Google Sheets 업로드 실패: {e}")
        
        print(f"\n데이터 저장 완료: {output_path}")
        print(f"총 {len(df)}개 아티스트 데이터 수집")
        
        return str(output_path)


if __name__ == "__main__":
    try:
        print("🎵 Spotify API 클라이언트 테스트 시작")
        client = SpotifyAPIClient()
        
        # 간단한 테스트
        print("\n🔍 BTS 검색 테스트...")
        artists = client.search_artist("BTS")
        if artists:
            print(f"✅ 검색 성공! 찾은 아티스트: {artists[0]['artist_name']}")
            print(f"   팔로워 수: {artists[0]['followers']:,}")
        
        # 전체 데이터 수집 및 저장
        print("\n📊 전체 아티스트 데이터 수집 시작...")
        output_file = client.save_artists_data()
        if output_file:
            print(f"✅ 데이터 저장 완료: {output_file}")
        
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()