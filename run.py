#!/usr/bin/env python3
"""
대시보드 실행 스크립트
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    """메인 실행 함수"""
    print("🎵 K-Pop 아티스트 대시보드 시작")
    print("=" * 50)
    
    # 환경 변수 체크
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env 파일이 없습니다.")
        print("💡 .env.example 파일을 참고해서 .env 파일을 생성하세요.")
        print("   Spotify API 키가 필요합니다.")
        print()
    
    # Streamlit 실행
    try:
        dashboard_path = Path("dashboard/streamlit_dashboard.py")
        if not dashboard_path.exists():
            print("❌ 대시보드 파일을 찾을 수 없습니다.")
            return
        
        print("🚀 대시보드를 시작합니다...")
        print("📱 브라우저에서 http://localhost:8501 에 접속하세요")
        print()
        
        # Streamlit 실행
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(dashboard_path),
            "--server.port", "8501"
        ])
        
    except KeyboardInterrupt:
        print("\n👋 대시보드를 종료합니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()