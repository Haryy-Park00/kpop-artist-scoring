#!/usr/bin/env python3
"""
K-Pop 아티스트 데이터 수집 스케줄러
주기적으로 SNS 링크 수집, 팔로워 데이터 수집 등을 자동화
"""
import os
import sys
import time
import schedule
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

# .env 파일 로드
try:
    from dotenv import load_dotenv
    env_path = PROJECT_ROOT / '.env'
    load_dotenv(env_path)
except ImportError:
    print("python-dotenv가 설치되지 않았습니다.")

from utils.logging_config import get_project_logger
from utils.error_handling import with_retry
from utils.slack_notifications import send_slack_notification
from config import get_config

logger = get_project_logger(__name__)


class KpopDataScheduler:
    """K-Pop 데이터 수집 스케줄러"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.last_sns_collection = None
        self.last_data_collection = None
        
    @with_retry(max_attempts=3)
    def run_sns_link_collection(self):
        """SNS 링크 수집 실행"""
        try:
            logger.info("=== SNS 링크 수집 시작 ===")
            send_slack_notification('start', 'SNS 링크 수집')
            
            # SNS 링크 수집 스크립트 실행
            result = subprocess.run([
                sys.executable, 
                str(self.project_root / "crawlers" / "sns_link_collector.py")
            ], capture_output=True, text=True, timeout=1800)  # 30분 제한
            
            if result.returncode == 0:
                logger.info("SNS 링크 수집 완료")
                self.last_sns_collection = datetime.now()
                
                # 성공 알림
                send_slack_notification('success', 'SNS 링크 수집 완료', 
                    details=[f"완료 시간: {self.last_sns_collection.strftime('%H:%M:%S')}"])
                return True
            else:
                logger.error(f"SNS 링크 수집 실패: {result.stderr}")
                send_slack_notification('error', 'SNS 링크 수집 실패', error_msg=result.stderr[:500])
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "SNS 링크 수집 시간 초과 (30분)"
            logger.error(error_msg)
            send_slack_notification('error', 'SNS 링크 수집 시간 초과', error_msg=error_msg)
            return False
        except Exception as e:
            logger.error(f"SNS 링크 수집 중 오류: {e}")
            send_slack_notification('error', 'SNS 링크 수집 오류', error_msg=str(e))
            return False
    
    @with_retry(max_attempts=2)
    def run_sns_data_collection(self):
        """SNS 데이터 수집 실행"""
        try:
            logger.info("=== SNS 데이터 수집 시작 ===")
            send_slack_notification('start', 'SNS 데이터 수집')
            
            # SNS 데이터 수집 스크립트 실행
            result = subprocess.run([
                sys.executable,
                str(self.project_root / "crawlers" / "sns_data_collector.py")
            ], capture_output=True, text=True, timeout=3600)  # 60분 제한
            
            if result.returncode == 0:
                logger.info("SNS 데이터 수집 완료")
                self.last_data_collection = datetime.now()
                
                # 성공 알림
                send_slack_notification('success', 'SNS 데이터 수집 완료',
                    details=[f"완료 시간: {self.last_data_collection.strftime('%H:%M:%S')}"])
                return True
            else:
                logger.error(f"SNS 데이터 수집 실패: {result.stderr}")
                send_slack_notification('error', 'SNS 데이터 수집 실패', error_msg=result.stderr[:500])
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "SNS 데이터 수집 시간 초과 (60분)"
            logger.error(error_msg)
            send_slack_notification('error', 'SNS 데이터 수집 시간 초과', error_msg=error_msg)
            return False
        except Exception as e:
            logger.error(f"SNS 데이터 수집 중 오류: {e}")
            send_slack_notification('error', 'SNS 데이터 수집 오류', error_msg=str(e))
            return False
    
    def run_weekly_workflow(self):
        """주간 워크플로우 실행"""
        logger.info("🚀 주간 워크플로우 시작")
        
        success_count = 0
        total_tasks = 2
        
        # 1. SNS 링크 수집
        if self.run_sns_link_collection():
            success_count += 1
            
            # SNS 링크 수집 성공 시에만 데이터 수집 진행
            time.sleep(30)  # 30초 대기
            
            # 2. SNS 데이터 수집
            if self.run_sns_data_collection():
                success_count += 1
        
        # 결과 리포트
        logger.info(f"주간 워크플로우 완료: {success_count}/{total_tasks} 성공")
        
        # Slack 완료 리포트 발송
        stats = {
            "성공한_작업": success_count,
            "전체_작업": total_tasks,
            "성공률": f"{(success_count/total_tasks)*100:.1f}%",
            "SNS_링크_수집": "완료" if self.last_sns_collection else "실패",
            "SNS_데이터_수집": "완료" if self.last_data_collection else "실패"
        }
        
        if success_count == total_tasks:
            logger.info("✅ 모든 작업 성공")
            send_slack_notification('complete', '주간 워크플로우 완료', stats=stats)
        else:
            logger.warning(f"⚠️ 일부 작업 실패 ({total_tasks - success_count}개)")
            send_slack_notification('warning', '주간 워크플로우 일부 실패', 
                details=[f"실패한 작업: {total_tasks - success_count}개", 
                        f"성공률: {(success_count/total_tasks)*100:.1f}%"])
    
    def run_daily_check(self):
        """일일 체크 및 간단한 작업"""
        logger.info("📊 일일 상태 체크")
        
        # 데이터 폴더 상태 체크
        data_path = self.project_root / "data"
        if data_path.exists():
            total_files = len(list(data_path.rglob("*.csv")))
            logger.info(f"데이터 파일 수: {total_files}개")
        
        # 로그 정리 (7일 이상 된 로그 파일 삭제)
        self.cleanup_old_logs()
    
    def cleanup_old_logs(self):
        """오래된 로그 파일 정리"""
        logs_path = self.project_root / "logs"
        if not logs_path.exists():
            return
            
        cutoff_date = datetime.now() - timedelta(days=7)
        cleaned_count = 0
        
        for log_file in logs_path.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    log_file.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"로그 파일 삭제 실패 {log_file}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"오래된 로그 파일 {cleaned_count}개 정리 완료")
    
    def start_scheduler(self):
        """스케줄러 시작"""
        logger.info("🎵 K-Pop 데이터 수집 스케줄러 시작")
        
        # 스케줄 설정
        schedule.every().monday.at("09:00").do(self.run_weekly_workflow)  # 매주 월요일 오전 9시
        schedule.every().day.at("08:00").do(self.run_daily_check)  # 매일 오전 8시
        
        logger.info("📅 스케줄 설정 완료:")
        logger.info("- 매주 월요일 09:00: 전체 데이터 수집")
        logger.info("- 매일 08:00: 일일 상태 체크")
        
        # 스케줄러 실행
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
            except KeyboardInterrupt:
                logger.info("스케줄러 종료")
                break
            except Exception as e:
                logger.error(f"스케줄러 오류: {e}")
                time.sleep(300)  # 5분 대기 후 재시도


def main():
    """메인 실행"""
    scheduler = KpopDataScheduler()
    
    # 명령행 인자 처리
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "sns-links":
            scheduler.run_sns_link_collection()
        elif command == "sns-data":
            scheduler.run_sns_data_collection()
        elif command == "weekly":
            scheduler.run_weekly_workflow()
        elif command == "daily":
            scheduler.run_daily_check()
        elif command == "start":
            scheduler.start_scheduler()
        else:
            print("사용법: python scheduler.py [sns-links|sns-data|weekly|daily|start]")
    else:
        # 기본값: 스케줄러 시작
        scheduler.start_scheduler()


if __name__ == "__main__":
    main()