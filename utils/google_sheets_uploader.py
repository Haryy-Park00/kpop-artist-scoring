"""
Google Sheets 업로더
CSV 파일을 Google Sheets에 자동으로 업로드하는 유틸리티
"""
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime

class GoogleSheetsUploader:
    def __init__(self, credentials_path=None):
        """
        Google Sheets 업로더 초기화
        
        Args:
            credentials_path: Google Service Account 키 파일 경로
        """
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CREDENTIALS_PATH')
        self.client = None
        self._authenticate()
    
    def _authenticate(self):
        """Google Sheets API 인증"""
        try:
            # 서비스 계정 키 파일을 사용한 인증
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            if self.credentials_path and os.path.exists(self.credentials_path):
                credentials = Credentials.from_service_account_file(
                    self.credentials_path, scopes=scope
                )
                self.client = gspread.authorize(credentials)
                print("✅ Google Sheets API 인증 완료")
            else:
                print("❌ Google 서비스 계정 키 파일을 찾을 수 없습니다.")
                print(f"경로: {self.credentials_path}")
                
        except Exception as e:
            print(f"❌ Google Sheets API 인증 실패: {e}")
    
    def upload_csv_to_sheet(self, csv_path, sheet_url, worksheet_name="Sheet1"):
        """
        CSV 파일을 Google Sheets에 업로드
        
        Args:
            csv_path: 업로드할 CSV 파일 경로
            sheet_url: Google Sheets URL 또는 스프레드시트 ID
            worksheet_name: 워크시트 이름 (기본값: Sheet1)
        """
        if not self.client:
            print("❌ Google Sheets 클라이언트가 인증되지 않았습니다.")
            return False
        
        try:
            # CSV 파일 읽기
            df = pd.read_csv(csv_path)
            print(f"📁 CSV 파일 로드: {csv_path}")
            print(f"   데이터 행 수: {len(df)}")
            
            # 스프레드시트 열기
            if sheet_url.startswith('http'):
                # URL에서 스프레드시트 ID 추출
                sheet_id = sheet_url.split('/d/')[1].split('/')[0]
                sheet = self.client.open_by_key(sheet_id)
            else:
                # 직접 ID 사용
                sheet = self.client.open_by_key(sheet_url)
            
            print(f"📊 스프레드시트 열기: {sheet.title}")
            
            # 워크시트 선택 또는 생성
            try:
                worksheet = sheet.worksheet(worksheet_name)
                print(f"   기존 워크시트 사용: {worksheet_name}")
            except gspread.WorksheetNotFound:
                worksheet = sheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
                print(f"   새 워크시트 생성: {worksheet_name}")
            
            # 기존 데이터 지우기
            worksheet.clear()
            
            # 헤더 추가
            headers = df.columns.tolist()
            worksheet.append_row(headers)
            
            # 데이터 업로드 (배치 업데이트 사용)
            data = df.values.tolist()
            if data:
                # None 값을 빈 문자열로 변환
                data = [[str(cell) if cell is not None else '' for cell in row] for row in data]
                worksheet.append_rows(data)
            
            print(f"✅ 업로드 완료!")
            print(f"   총 {len(data)}행의 데이터가 업로드되었습니다.")
            print(f"   스프레드시트 URL: https://docs.google.com/spreadsheets/d/{sheet.id}")
            
            return True
            
        except Exception as e:
            print(f"❌ 업로드 실패: {e}")
            return False
    
    def create_new_sheet(self, title, csv_path=None, share_emails=None):
        """
        새 Google Sheets 생성
        
        Args:
            title: 스프레드시트 제목
            csv_path: 초기 데이터로 사용할 CSV 파일 경로 (선택사항)
            share_emails: 공유할 이메일 리스트 (선택사항)
        
        Returns:
            str: 생성된 스프레드시트 URL
        """
        if not self.client:
            print("❌ Google Sheets 클라이언트가 인증되지 않았습니다.")
            return None
        
        try:
            # 새 스프레드시트 생성
            sheet = self.client.create(title)
            print(f"📊 새 스프레드시트 생성: {title}")
            print(f"   URL: https://docs.google.com/spreadsheets/d/{sheet.id}")
            
            # 기본 공유 이메일 설정
            if not share_emails:
                share_emails = os.getenv('GOOGLE_SHEETS_SHARE_EMAILS', '').split(',')
                share_emails = [email.strip() for email in share_emails if email.strip()]
            
            # harry@bigc.im을 기본으로 추가
            if 'harry@bigc.im' not in share_emails:
                share_emails.append('harry@bigc.im')
            
            # 이메일 주소들에 편집자 권한 부여
            for email in share_emails:
                if email:
                    try:
                        sheet.share(email, perm_type='user', role='writer')
                        print(f"   ✅ 편집자 권한 부여: {email}")
                    except Exception as e:
                        print(f"   ⚠️ 권한 부여 실패 ({email}): {e}")
            
            # CSV 데이터가 있으면 업로드
            if csv_path and os.path.exists(csv_path):
                self.upload_csv_to_sheet(csv_path, sheet.id)
            
            return f"https://docs.google.com/spreadsheets/d/{sheet.id}"
            
        except Exception as e:
            print(f"❌ 스프레드시트 생성 실패: {e}")
            return None
    
    def share_sheet(self, sheet_url, emails, role='writer'):
        """
        기존 스프레드시트에 권한 부여
        
        Args:
            sheet_url: Google Sheets URL 또는 스프레드시트 ID
            emails: 공유할 이메일 주소 (문자열 또는 리스트)
            role: 권한 레벨 ('reader', 'writer', 'owner')
        
        Returns:
            bool: 성공 여부
        """
        if not self.client:
            print("❌ Google Sheets 클라이언트가 인증되지 않았습니다.")
            return False
        
        try:
            # 스프레드시트 열기
            if sheet_url.startswith('http'):
                sheet_id = sheet_url.split('/d/')[1].split('/')[0]
                sheet = self.client.open_by_key(sheet_id)
            else:
                sheet = self.client.open_by_key(sheet_url)
            
            # 이메일 리스트 처리
            if isinstance(emails, str):
                emails = [emails]
            
            # 각 이메일에 권한 부여
            for email in emails:
                if email.strip():
                    try:
                        sheet.share(email.strip(), perm_type='user', role=role)
                        print(f"   ✅ {role} 권한 부여: {email}")
                    except Exception as e:
                        print(f"   ⚠️ 권한 부여 실패 ({email}): {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ 권한 부여 실패: {e}")
            return False

def main():
    """테스트 함수"""
    # 최신 Spotify 데이터 파일 찾기
    data_dir = "/Users/hanbin/Desktop/DB_RPA_Project/data/follower"
    if os.path.exists(data_dir):
        files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        if files:
            latest_file = max([os.path.join(data_dir, f) for f in files], 
                            key=os.path.getmtime)
            
            print(f"🎵 최신 Spotify 데이터 파일: {latest_file}")
            
            # Google Sheets 업로더 초기화
            uploader = GoogleSheetsUploader()
            
            if uploader.client:
                # 새 스프레드시트 생성 및 데이터 업로드
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                title = f"Spotify_데이터_{timestamp}"
                
                sheet_url = uploader.create_new_sheet(title, latest_file)
                if sheet_url:
                    print(f"✅ 완료! 스프레드시트가 생성되었습니다: {sheet_url}")
        else:
            print("❌ CSV 파일을 찾을 수 없습니다.")
    else:
        print("❌ 데이터 디렉토리를 찾을 수 없습니다.")

if __name__ == "__main__":
    main()