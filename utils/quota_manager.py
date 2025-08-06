"""
API 할당량 관리 및 최적화
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import requests

from utils.path_utils import get_path


class APIQuotaManager:
    """API 할당량 관리자"""
    
    def __init__(self):
        self.quota_file = get_path("data") / "api_quota_status.json"
        self.quota_limits = {
            'youtube': {
                'daily_limit': 10000,  # 일일 10,000 유닛
                'search_cost': 100,    # 검색 1회당 100 유닛
                'channel_cost': 1,     # 채널 정보 1개당 1 유닛
                'reset_time': '00:00'  # 매일 자정 리셋
            },
            'spotify': {
                'daily_limit': 100000,  # 실제로는 무제한이지만 안전을 위해
                'search_cost': 1,
                'artist_cost': 1,
                'reset_time': '00:00'
            },
            'kopis': {
                'daily_limit': 1000,   # 추정값
                'search_cost': 1,
                'detail_cost': 1,
                'reset_time': '00:00'
            }
        }
        self.load_quota_status()
    
    def load_quota_status(self):
        """할당량 상태 로드"""
        try:
            if self.quota_file.exists():
                with open(self.quota_file, 'r', encoding='utf-8') as f:
                    self.quota_status = json.load(f)
            else:
                self.quota_status = {}
            
            # 오늘 날짜로 초기화
            today = datetime.now().strftime('%Y-%m-%d')
            for api in self.quota_limits:
                if api not in self.quota_status:
                    self.quota_status[api] = {}
                
                if today not in self.quota_status[api]:
                    self.quota_status[api][today] = {
                        'used': 0,
                        'remaining': self.quota_limits[api]['daily_limit'],
                        'requests': []
                    }
                    
        except Exception as e:
            print(f"할당량 상태 로드 실패: {e}")
            self.quota_status = {}
    
    def save_quota_status(self):
        """할당량 상태 저장"""
        try:
            self.quota_file.parent.mkdir(exist_ok=True)
            with open(self.quota_file, 'w', encoding='utf-8') as f:
                json.dump(self.quota_status, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"할당량 상태 저장 실패: {e}")
    
    def check_quota(self, api: str, cost: int) -> bool:
        """할당량 확인"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if api not in self.quota_status:
            return False
        
        if today not in self.quota_status[api]:
            return True
        
        remaining = self.quota_status[api][today]['remaining']
        return remaining >= cost
    
    def use_quota(self, api: str, operation: str, cost: int) -> bool:
        """할당량 사용"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if not self.check_quota(api, cost):
            return False
        
        # 할당량 차감
        if api not in self.quota_status:
            self.quota_status[api] = {}
        
        if today not in self.quota_status[api]:
            self.quota_status[api][today] = {
                'used': 0,
                'remaining': self.quota_limits[api]['daily_limit'],
                'requests': []
            }
        
        self.quota_status[api][today]['used'] += cost
        self.quota_status[api][today]['remaining'] -= cost
        self.quota_status[api][today]['requests'].append({
            'time': datetime.now().isoformat(),
            'operation': operation,
            'cost': cost
        })
        
        self.save_quota_status()
        return True
    
    def get_quota_status(self, api: str) -> Dict:
        """현재 할당량 상태 조회"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if api not in self.quota_status or today not in self.quota_status[api]:
            return {
                'used': 0,
                'remaining': self.quota_limits[api]['daily_limit'],
                'limit': self.quota_limits[api]['daily_limit'],
                'usage_percent': 0
            }
        
        status = self.quota_status[api][today]
        limit = self.quota_limits[api]['daily_limit']
        
        return {
            'used': status['used'],
            'remaining': status['remaining'],
            'limit': limit,
            'usage_percent': (status['used'] / limit) * 100
        }
    
    def estimate_batch_cost(self, api: str, operations: Dict[str, int]) -> int:
        """배치 작업 비용 추정"""
        total_cost = 0
        
        for operation, count in operations.items():
            if api == 'youtube':
                if operation == 'search':
                    total_cost += count * self.quota_limits[api]['search_cost']
                elif operation == 'channel_info':
                    total_cost += count * self.quota_limits[api]['channel_cost']
            elif api in ['spotify', 'kopis']:
                total_cost += count * self.quota_limits[api].get(f'{operation}_cost', 1)
        
        return total_cost
    
    def optimize_batch_size(self, api: str, total_items: int, operation_type: str) -> int:
        """최적 배치 크기 계산"""
        status = self.get_quota_status(api)
        remaining = status['remaining']
        
        if api == 'youtube':
            if operation_type == 'search':
                cost_per_item = self.quota_limits[api]['search_cost']
            else:
                cost_per_item = self.quota_limits[api]['channel_cost']
        else:
            cost_per_item = 1
        
        max_items = remaining // cost_per_item
        return min(total_items, max_items)
    
    def schedule_requests(self, api: str, total_items: int, operation_type: str) -> list:
        """요청 스케줄링"""
        optimal_batch = self.optimize_batch_size(api, total_items, operation_type)
        
        if optimal_batch >= total_items:
            # 한 번에 모든 작업 가능
            return [{'batch_size': total_items, 'delay': 0}]
        
        # 여러 배치로 분할
        batches = []
        remaining_items = total_items
        
        while remaining_items > 0:
            batch_size = min(optimal_batch, remaining_items)
            batches.append({
                'batch_size': batch_size,
                'delay': 1 if len(batches) > 0 else 0  # 첫 배치 제외하고 1초 지연
            })
            remaining_items -= batch_size
        
        return batches
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """오래된 할당량 데이터 정리"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        for api in self.quota_status:
            dates_to_remove = []
            for date_str in self.quota_status[api]:
                if date_str < cutoff_str:
                    dates_to_remove.append(date_str)
            
            for date_str in dates_to_remove:
                del self.quota_status[api][date_str]
        
        self.save_quota_status()


class RateLimiter:
    """요청 속도 제한"""
    
    def __init__(self):
        self.last_requests = {}
        self.rate_limits = {
            'youtube': 1.0,   # 1초당 1요청
            'spotify': 0.1,   # 0.1초당 1요청 (더 관대함)
            'kopis': 2.0      # 2초당 1요청 (보수적)
        }
    
    def wait_if_needed(self, api: str):
        """필요시 대기"""
        if api not in self.rate_limits:
            return
        
        now = time.time()
        rate_limit = self.rate_limits[api]
        
        if api in self.last_requests:
            elapsed = now - self.last_requests[api]
            if elapsed < rate_limit:
                wait_time = rate_limit - elapsed
                time.sleep(wait_time)
        
        self.last_requests[api] = time.time()


# 전역 인스턴스
quota_manager = APIQuotaManager()
rate_limiter = RateLimiter()


def with_quota_check(api: str, operation: str, cost: int = 1):
    """할당량 체크 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 할당량 확인
            if not quota_manager.check_quota(api, cost):
                raise Exception(f"{api} API 할당량이 부족합니다. 필요: {cost}, 남은량: {quota_manager.get_quota_status(api)['remaining']}")
            
            # 속도 제한
            rate_limiter.wait_if_needed(api)
            
            try:
                # 할당량 사용
                quota_manager.use_quota(api, operation, cost)
                
                # 실제 함수 실행
                result = func(*args, **kwargs)
                
                return result
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    # 할당량 초과로 간주
                    print(f"⚠️ {api} API 할당량 초과 감지")
                raise
            
        return wrapper
    return decorator