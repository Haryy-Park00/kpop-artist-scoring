"""
마스터 대시보드 Google Sheets 생성기
모든 주간 데이터를 통합하여 하나의 마스터 시트에 관리
"""
import pandas as pd
import sqlite3
from pathlib import Path
import sys
from datetime import datetime
import os

sys.path.append(str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.google_sheets_uploader import GoogleSheetsUploader

class MasterDashboardCreator:
    def __init__(self):
        self.db_path = Path("data/database/spotify_weekly.db")
        self.uploader = GoogleSheetsUploader()
        
    def create_master_dashboard(self):
        """마스터 대시보드 Google Sheets 생성"""
        if not self.uploader.client:
            print("❌ Google Sheets 클라이언트 인증 실패")
            return None
        
        # 스프레드시트 생성
        timestamp = datetime.now().strftime("%Y%m%d")
        sheet_title = f"Spotify_마스터_대시보드_{timestamp}"
        
        sheet = self.uploader.client.create(sheet_title)
        print(f"📊 마스터 대시보드 생성: {sheet.title}")
        
        # 기본 권한 부여
        emails = os.getenv('GOOGLE_SHEETS_SHARE_EMAILS', '').split(',')
        emails = [email.strip() for email in emails if email.strip()]
        if 'harry@bigc.im' not in emails:
            emails.append('harry@bigc.im')
        
        for email in emails:
            if email:
                try:
                    sheet.share(email, perm_type='user', role='writer')
                    print(f"   ✅ 편집자 권한 부여: {email}")
                except Exception as e:
                    print(f"   ⚠️ 권한 부여 실패 ({email}): {e}")
        
        # 워크시트들 생성
        self.create_summary_sheet(sheet)
        self.create_weekly_data_sheet(sheet)
        self.create_artist_master_sheet(sheet)
        self.create_growth_analysis_sheet(sheet)
        
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet.id}"
        print(f"✅ 마스터 대시보드 완료: {sheet_url}")
        
        return sheet_url
    
    def create_summary_sheet(self, sheet):
        """요약 시트 생성"""
        try:
            summary_ws = sheet.add_worksheet(title="📊 주간 요약", rows=100, cols=10)
            
            # 헤더 설정
            headers = [
                "수집 날짜", "년도", "주차", "아티스트 수", 
                "평균 팔로워", "최고 팔로워", "최저 팔로워", "평균 인기도"
            ]
            summary_ws.append_row(headers)
            
            # 데이터 로드
            if self.db_path.exists():
                conn = sqlite3.connect(self.db_path)
                query = '''
                    SELECT 
                        collection_date,
                        year, 
                        week,
                        COUNT(*) as artist_count,
                        ROUND(AVG(followers), 0) as avg_followers,
                        MAX(followers) as max_followers,
                        MIN(followers) as min_followers,
                        ROUND(AVG(popularity), 1) as avg_popularity
                    FROM weekly_data 
                    GROUP BY collection_date, year, week
                    ORDER BY collection_date DESC
                    LIMIT 20
                '''
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                # 데이터 추가
                for _, row in df.iterrows():
                    summary_ws.append_row(row.tolist())
            
            print("   ✅ 주간 요약 시트 생성 완료")
            
        except Exception as e:
            print(f"   ❌ 주간 요약 시트 생성 실패: {e}")
    
    def create_weekly_data_sheet(self, sheet):
        """주간 데이터 시트 생성"""
        try:
            # 기본 Sheet1을 주간 데이터로 변경
            weekly_ws = sheet.sheet1
            weekly_ws.update_title("📈 최신 주간 데이터")
            
            # 헤더 설정
            headers = [
                "아티스트 ID", "아티스트명", "인기도", "팔로워", 
                "장르", "Spotify URL", "원본명", "업데이트 날짜"
            ]
            weekly_ws.append_row(headers)
            
            # 최신 데이터 로드
            if self.db_path.exists():
                conn = sqlite3.connect(self.db_path)
                query = '''
                    SELECT 
                        artist_id, artist_name, popularity, followers,
                        genres, spotify_url, original_name, collection_date
                    FROM weekly_data 
                    WHERE collection_date = (SELECT MAX(collection_date) FROM weekly_data)
                    ORDER BY followers DESC
                '''
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                # 데이터 추가 (배치로 처리)
                if not df.empty:
                    data = df.fillna('').values.tolist()
                    weekly_ws.append_rows(data)
            
            print("   ✅ 주간 데이터 시트 생성 완료")
            
        except Exception as e:
            print(f"   ❌ 주간 데이터 시트 생성 실패: {e}")
    
    def create_artist_master_sheet(self, sheet):
        """아티스트 마스터 시트 생성"""
        try:
            master_ws = sheet.add_worksheet(title="👥 아티스트 마스터", rows=1000, cols=8)
            
            # 헤더 설정
            headers = [
                "아티스트 ID", "아티스트명", "Spotify URL", 
                "첫 등장", "마지막 업데이트", "총 등장 횟수", "최신 팔로워", "최신 인기도"
            ]
            master_ws.append_row(headers)
            
            # 데이터 로드
            if self.db_path.exists():
                conn = sqlite3.connect(self.db_path)
                query = '''
                    SELECT 
                        m.artist_id,
                        m.artist_name,
                        m.spotify_url,
                        m.first_seen,
                        m.last_updated,
                        COUNT(w.artist_id) as appearance_count,
                        COALESCE(latest.followers, 0) as latest_followers,
                        COALESCE(latest.popularity, 0) as latest_popularity
                    FROM artists_master m
                    LEFT JOIN weekly_data w ON m.artist_id = w.artist_id
                    LEFT JOIN (
                        SELECT artist_id, followers, popularity
                        FROM weekly_data w1
                        WHERE collection_date = (SELECT MAX(collection_date) FROM weekly_data w2 WHERE w2.artist_id = w1.artist_id)
                    ) latest ON m.artist_id = latest.artist_id
                    GROUP BY m.artist_id, m.artist_name, m.spotify_url, m.first_seen, m.last_updated
                    ORDER BY latest_followers DESC
                '''
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                # 데이터 추가
                if not df.empty:
                    data = df.fillna('').values.tolist()
                    master_ws.append_rows(data)
            
            print("   ✅ 아티스트 마스터 시트 생성 완료")
            
        except Exception as e:
            print(f"   ❌ 아티스트 마스터 시트 생성 실패: {e}")
    
    def create_growth_analysis_sheet(self, sheet):
        """성장 분석 시트 생성"""
        try:
            growth_ws = sheet.add_worksheet(title="📊 성장 분석", rows=200, cols=10)
            
            # 헤더 설정
            headers = [
                "아티스트명", "현재 팔로워", "지난주 대비 변화", 
                "인기도 변화", "성장률(%)", "수집 날짜", "상태"
            ]
            growth_ws.append_row(headers)
            
            # 성장 데이터 로드
            if self.db_path.exists():
                conn = sqlite3.connect(self.db_path)
                query = '''
                    SELECT 
                        a.artist_name,
                        h.followers,
                        h.follower_change,
                        h.popularity_change,
                        CASE 
                            WHEN h.followers - h.follower_change > 0 
                            THEN ROUND((CAST(h.follower_change AS REAL) / (h.followers - h.follower_change)) * 100, 2)
                            ELSE 0 
                        END as growth_rate,
                        h.collection_date,
                        CASE 
                            WHEN h.follower_change > 0 THEN '📈 상승'
                            WHEN h.follower_change < 0 THEN '📉 하락'
                            ELSE '➡️ 유지'
                        END as status
                    FROM follower_history h
                    JOIN artists_master a ON h.artist_id = a.artist_id
                    WHERE h.collection_date >= date('now', '-4 weeks')
                    ORDER BY h.collection_date DESC, h.follower_change DESC
                    LIMIT 100
                '''
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                # 데이터 추가
                if not df.empty:
                    data = df.fillna('').values.tolist()
                    growth_ws.append_rows(data)
            
            print("   ✅ 성장 분석 시트 생성 완료")
            
        except Exception as e:
            print(f"   ❌ 성장 분석 시트 생성 실패: {e}")
    
    def update_existing_dashboard(self, sheet_url):
        """기존 대시보드 업데이트"""
        try:
            # URL에서 스프레드시트 ID 추출
            sheet_id = sheet_url.split('/d/')[1].split('/')[0]
            sheet = self.uploader.client.open_by_key(sheet_id)
            
            print(f"📊 기존 대시보드 업데이트: {sheet.title}")
            
            # 각 시트 업데이트
            self.update_summary_sheet(sheet)
            self.update_weekly_data_sheet(sheet)
            self.update_growth_analysis_sheet(sheet)
            
            print("✅ 대시보드 업데이트 완료")
            return True
            
        except Exception as e:
            print(f"❌ 대시보드 업데이트 실패: {e}")
            return False
    
    def update_summary_sheet(self, sheet):
        """요약 시트 업데이트"""
        try:
            summary_ws = sheet.worksheet("📊 주간 요약")
            summary_ws.clear()
            
            # 헤더 재설정
            headers = [
                "수집 날짜", "년도", "주차", "아티스트 수", 
                "평균 팔로워", "최고 팔로워", "최저 팔로워", "평균 인기도"
            ]
            summary_ws.append_row(headers)
            
            # 새 데이터 로드
            if self.db_path.exists():
                conn = sqlite3.connect(self.db_path)
                query = '''
                    SELECT 
                        collection_date, year, week,
                        COUNT(*) as artist_count,
                        ROUND(AVG(followers), 0) as avg_followers,
                        MAX(followers) as max_followers,
                        MIN(followers) as min_followers,
                        ROUND(AVG(popularity), 1) as avg_popularity
                    FROM weekly_data 
                    GROUP BY collection_date, year, week
                    ORDER BY collection_date DESC
                    LIMIT 20
                '''
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                if not df.empty:
                    data = df.fillna('').values.tolist()
                    summary_ws.append_rows(data)
                    
        except Exception as e:
            print(f"   ⚠️ 요약 시트 업데이트 실패: {e}")
    
    def update_weekly_data_sheet(self, sheet):
        """주간 데이터 시트 업데이트"""
        try:
            weekly_ws = sheet.worksheet("📈 최신 주간 데이터")
            weekly_ws.clear()
            
            # 헤더 재설정
            headers = [
                "아티스트 ID", "아티스트명", "인기도", "팔로워", 
                "장르", "Spotify URL", "원본명", "업데이트 날짜"
            ]
            weekly_ws.append_row(headers)
            
            # 최신 데이터 로드
            if self.db_path.exists():
                conn = sqlite3.connect(self.db_path)
                query = '''
                    SELECT 
                        artist_id, artist_name, popularity, followers,
                        genres, spotify_url, original_name, collection_date
                    FROM weekly_data 
                    WHERE collection_date = (SELECT MAX(collection_date) FROM weekly_data)
                    ORDER BY followers DESC
                '''
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                if not df.empty:
                    data = df.fillna('').values.tolist()
                    weekly_ws.append_rows(data)
                    
        except Exception as e:
            print(f"   ⚠️ 주간 데이터 시트 업데이트 실패: {e}")
    
    def update_growth_analysis_sheet(self, sheet):
        """성장 분석 시트 업데이트"""
        try:
            growth_ws = sheet.worksheet("📊 성장 분석")
            growth_ws.clear()
            
            # 헤더 재설정
            headers = [
                "아티스트명", "현재 팔로워", "지난주 대비 변화", 
                "인기도 변화", "성장률(%)", "수집 날짜", "상태"
            ]
            growth_ws.append_row(headers)
            
            # 성장 데이터 로드
            if self.db_path.exists():
                conn = sqlite3.connect(self.db_path)
                query = '''
                    SELECT 
                        a.artist_name, h.followers, h.follower_change, h.popularity_change,
                        CASE 
                            WHEN h.followers - h.follower_change > 0 
                            THEN ROUND((CAST(h.follower_change AS REAL) / (h.followers - h.follower_change)) * 100, 2)
                            ELSE 0 
                        END as growth_rate,
                        h.collection_date,
                        CASE 
                            WHEN h.follower_change > 0 THEN '📈 상승'
                            WHEN h.follower_change < 0 THEN '📉 하락'
                            ELSE '➡️ 유지'
                        END as status
                    FROM follower_history h
                    JOIN artists_master a ON h.artist_id = a.artist_id
                    WHERE h.collection_date >= date('now', '-4 weeks')
                    ORDER BY h.collection_date DESC, h.follower_change DESC
                    LIMIT 100
                '''
                df = pd.read_sql_query(query, conn)
                conn.close()
                
                if not df.empty:
                    data = df.fillna('').values.tolist()
                    growth_ws.append_rows(data)
                    
        except Exception as e:
            print(f"   ⚠️ 성장 분석 시트 업데이트 실패: {e}")

def main():
    creator = MasterDashboardCreator()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            # 새 마스터 대시보드 생성
            sheet_url = creator.create_master_dashboard()
            if sheet_url:
                print(f"\n🎉 마스터 대시보드가 생성되었습니다!")
                print(f"🔗 URL: {sheet_url}")
        
        elif command == "update":
            # 기존 대시보드 업데이트
            if len(sys.argv) > 2:
                sheet_url = sys.argv[2]
                success = creator.update_existing_dashboard(sheet_url)
                if success:
                    print("🎉 대시보드 업데이트 완료!")
            else:
                print("사용법: python master_dashboard_creator.py update <시트_URL>")
        
        else:
            print("사용법:")
            print("  python master_dashboard_creator.py create           # 새 대시보드 생성")
            print("  python master_dashboard_creator.py update <URL>     # 기존 대시보드 업데이트")
    else:
        print("사용법:")
        print("  python master_dashboard_creator.py create           # 새 대시보드 생성")
        print("  python master_dashboard_creator.py update <URL>     # 기존 대시보드 업데이트")

if __name__ == "__main__":
    main()