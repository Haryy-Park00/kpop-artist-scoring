#!/usr/bin/env python3
"""
Slack 알림 모듈
K-Pop 데이터 수집 상태를 Slack으로 실시간 알림
"""
import os
import json
import requests
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass

from utils.logging_config import get_project_logger

logger = get_project_logger(__name__)


@dataclass
class SlackMessage:
    """Slack 메시지 구조"""
    text: str
    color: str = "good"  # good(green), warning(yellow), danger(red)
    emoji: str = ":robot_face:"
    username: str = "K-Pop Data Bot"


class SlackNotifier:
    """Slack 알림 발송 클래스"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Args:
            webhook_url: Slack 웹훅 URL (환경변수 SLACK_WEBHOOK_URL 사용 가능)
        """
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
        self.enabled = bool(self.webhook_url)
        
        if not self.enabled:
            logger.info("Slack 웹훅 URL이 설정되지 않았습니다. 알림이 비활성화됩니다.")
    
    def send_message(self, message: SlackMessage) -> bool:
        """
        Slack 메시지 발송
        
        Args:
            message: 발송할 메시지 객체
            
        Returns:
            성공 여부
        """
        if not self.enabled:
            logger.debug(f"Slack 알림 비활성화: {message.text}")
            return False
        
        try:
            payload = {
                "username": message.username,
                "icon_emoji": message.emoji,
                "attachments": [
                    {
                        "color": message.color,
                        "text": message.text,
                        "footer": "K-Pop Artist Scoring System",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug("Slack 메시지 발송 성공")
                return True
            else:
                logger.error(f"Slack 메시지 발송 실패: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Slack 알림 발송 중 오류: {e}")
            return False
    
    def send_success(self, title: str, details: List[str] = None) -> bool:
        """성공 알림 발송"""
        text = f"✅ **{title}**\n"
        if details:
            text += "\n".join(f"• {detail}" for detail in details)
        
        message = SlackMessage(
            text=text,
            color="good",
            emoji=":white_check_mark:"
        )
        return self.send_message(message)
    
    def send_warning(self, title: str, details: List[str] = None) -> bool:
        """경고 알림 발송"""
        text = f"⚠️ **{title}**\n"
        if details:
            text += "\n".join(f"• {detail}" for detail in details)
        
        message = SlackMessage(
            text=text,
            color="warning",
            emoji=":warning:"
        )
        return self.send_message(message)
    
    def send_error(self, title: str, error_msg: str = None, details: List[str] = None) -> bool:
        """에러 알림 발송"""
        text = f"❌ **{title}**\n"
        if error_msg:
            text += f"```{error_msg}```\n"
        if details:
            text += "\n".join(f"• {detail}" for detail in details)
        
        message = SlackMessage(
            text=text,
            color="danger",
            emoji=":x:"
        )
        return self.send_message(message)
    
    def send_start_notification(self, task_name: str) -> bool:
        """작업 시작 알림"""
        return self.send_message(SlackMessage(
            text=f"🚀 **{task_name} 시작**\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            color="good",
            emoji=":rocket:"
        ))
    
    def send_completion_report(self, task_name: str, stats: Dict) -> bool:
        """작업 완료 리포트"""
        text = f"📊 **{task_name} 완료**\n"
        
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                if key.endswith('_count') or key.startswith('total_'):
                    text += f"• {key.replace('_', ' ').title()}: {value:,}\n"
                else:
                    text += f"• {key.replace('_', ' ').title()}: {value}\n"
            else:
                text += f"• {key.replace('_', ' ').title()}: {value}\n"
        
        text += f"\n완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_message(SlackMessage(
            text=text,
            color="good",
            emoji=":chart_with_upwards_trend:"
        ))
    
    def send_daily_summary(self, summary_data: Dict) -> bool:
        """일일 요약 보고서"""
        text = "📈 **일일 데이터 수집 요약**\n\n"
        
        # 기본 통계
        if 'collected_artists' in summary_data:
            text += f"🎤 수집된 아티스트: {summary_data['collected_artists']:,}명\n"
        
        if 'sns_links_found' in summary_data:
            text += f"🔗 발견된 SNS 링크: {summary_data['sns_links_found']:,}개\n"
        
        if 'total_followers' in summary_data:
            text += f"👥 총 팔로워 수: {summary_data['total_followers']:,}명\n"
        
        # 플랫폼별 통계
        platforms = ['instagram', 'youtube', 'twitter']
        for platform in platforms:
            count_key = f"{platform}_count"
            if count_key in summary_data:
                emoji = {"instagram": "📸", "youtube": "🎵", "twitter": "🐦"}[platform]
                text += f"{emoji} {platform.title()}: {summary_data[count_key]:,}개\n"
        
        # 에러 정보
        if 'errors' in summary_data and summary_data['errors'] > 0:
            text += f"⚠️ 에러 발생: {summary_data['errors']}건\n"
        
        text += f"\n📅 리포트 생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_message(SlackMessage(
            text=text,
            color="good",
            emoji=":calendar:"
        ))


# 전역 알림 객체
slack_notifier = SlackNotifier()


def send_slack_notification(message_type: str, title: str, **kwargs) -> bool:
    """
    간편한 Slack 알림 발송 함수
    
    Args:
        message_type: 'success', 'warning', 'error', 'start', 'complete', 'summary'
        title: 알림 제목
        **kwargs: 추가 파라미터
    """
    if message_type == 'success':
        return slack_notifier.send_success(title, kwargs.get('details'))
    elif message_type == 'warning':
        return slack_notifier.send_warning(title, kwargs.get('details'))
    elif message_type == 'error':
        return slack_notifier.send_error(title, kwargs.get('error_msg'), kwargs.get('details'))
    elif message_type == 'start':
        return slack_notifier.send_start_notification(title)
    elif message_type == 'complete':
        return slack_notifier.send_completion_report(title, kwargs.get('stats', {}))
    elif message_type == 'summary':
        return slack_notifier.send_daily_summary(kwargs.get('data', {}))
    else:
        logger.error(f"알 수 없는 메시지 타입: {message_type}")
        return False


# 테스트 함수
def test_slack_notification():
    """Slack 알림 테스트"""
    notifier = SlackNotifier()
    
    if not notifier.enabled:
        print("❌ Slack 웹훅 URL이 설정되지 않았습니다.")
        print("환경변수 SLACK_WEBHOOK_URL을 설정해주세요.")
        return False
    
    print("🧪 Slack 알림 테스트 중...")
    
    # 테스트 메시지 발송
    success = notifier.send_success(
        "테스트 알림",
        ["K-Pop 데이터 수집 시스템이 정상적으로 작동합니다", 
         "Slack 알림이 성공적으로 설정되었습니다"]
    )
    
    if success:
        print("✅ Slack 알림 테스트 성공!")
        return True
    else:
        print("❌ Slack 알림 테스트 실패")
        return False


if __name__ == "__main__":
    test_slack_notification()