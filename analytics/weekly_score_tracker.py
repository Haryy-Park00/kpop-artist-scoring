#!/usr/bin/env python3
"""
BigC 아티스트 주간 스코어 변화 추적 시스템
주간별 스코어 상승률/하락률 계산 및 트렌드 분석
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import glob
from datetime import datetime, timedelta
import json

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from utils.scoring import calculate_artist_score

class WeeklyScoreTracker:
    def __init__(self):
        self.project_root = project_root
        self.data_dir = project_root / "data" / "bigc_pipeline"
        self.analytics_dir = project_root / "analytics" / "weekly_trends"
        self.analytics_dir.mkdir(parents=True, exist_ok=True)
        
    def get_weekly_data_files(self):
        """주간별 데이터 파일 목록 가져오기"""
        pattern = str(self.data_dir / "*빅크*SNS팔로워*.csv")
        files = glob.glob(pattern)
        
        # 파일명에서 날짜 추출하여 정렬
        file_data = []
        for file_path in files:
            try:
                file_name = Path(file_path).name
                # 파일명에서 날짜 부분 추출 (예: 20250804_131055)
                date_part = file_name.split('_')[-2]  # 20250804
                date_obj = datetime.strptime(date_part, '%Y%m%d')
                file_data.append({
                    'path': file_path,
                    'date': date_obj,
                    'week': f"{date_obj.year}년_{date_obj.isocalendar()[1]}주차"
                })
            except (ValueError, IndexError):
                continue
        
        # 날짜순 정렬
        file_data.sort(key=lambda x: x['date'])
        return file_data
    
    def calculate_weekly_scores(self, df):
        """주간 데이터의 스코어 계산"""
        if df is None or df.empty:
            return df
        
        df_copy = df.copy()
        df_copy['total_score'] = df_copy.apply(calculate_artist_score, axis=1)
        return df_copy
    
    def compare_weekly_scores(self, current_df, previous_df):
        """두 주간 데이터 비교하여 변화율 계산"""
        if current_df is None or previous_df is None:
            return None
        
        # 공통 아티스트만 비교
        current_scores = current_df.set_index('artist')['total_score']
        previous_scores = previous_df.set_index('artist')['total_score']
        
        # 두 데이터에 모두 존재하는 아티스트
        common_artists = current_scores.index.intersection(previous_scores.index)
        
        if len(common_artists) == 0:
            return None
        
        comparison_data = []
        for artist in common_artists:
            current_score = current_scores[artist]
            previous_score = previous_scores[artist]
            
            # 변화율 계산
            if previous_score > 0:
                change_rate = ((current_score - previous_score) / previous_score) * 100
            else:
                change_rate = 0 if current_score == 0 else 100
            
            # 아티스트 정보 가져오기
            artist_info = current_df[current_df['artist'] == artist].iloc[0]
            
            comparison_data.append({
                'artist': artist,
                'entertainment': artist_info['entertainment'],
                'current_score': current_score,
                'previous_score': previous_score,
                'score_change': current_score - previous_score,
                'change_rate': change_rate,
                'trend': 'up' if change_rate > 0 else 'down' if change_rate < 0 else 'stable'
            })
        
        return pd.DataFrame(comparison_data)
    
    def generate_weekly_trends(self):
        """주간 트렌드 데이터 생성"""
        file_data = self.get_weekly_data_files()
        
        if len(file_data) < 2:
            print("❌ 주간 비교를 위해서는 최소 2개의 데이터 파일이 필요합니다.")
            return None
        
        print(f"📊 {len(file_data)}개 주간 데이터 파일 발견")
        
        trends_data = []
        
        for i in range(1, len(file_data)):
            current_file = file_data[i]
            previous_file = file_data[i-1]
            
            print(f"📈 {previous_file['week']} vs {current_file['week']} 비교 중...")
            
            # 데이터 로드
            current_df = pd.read_csv(current_file['path'])
            previous_df = pd.read_csv(previous_file['path'])
            
            # 스코어 계산
            current_df = self.calculate_weekly_scores(current_df)
            previous_df = self.calculate_weekly_scores(previous_df)
            
            # 비교 분석
            comparison = self.compare_weekly_scores(current_df, previous_df)
            
            if comparison is not None:
                comparison['current_week'] = current_file['week']
                comparison['previous_week'] = previous_file['week']
                comparison['current_date'] = current_file['date'].strftime('%Y-%m-%d')
                comparison['previous_date'] = previous_file['date'].strftime('%Y-%m-%d')
                
                trends_data.append(comparison)
        
        if trends_data:
            # 모든 트렌드 데이터 통합
            all_trends = pd.concat(trends_data, ignore_index=True)
            
            # 결과 저장
            output_file = self.analytics_dir / f"weekly_trends_{datetime.now().strftime('%Y%m%d')}.csv"
            all_trends.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            print(f"✅ 주간 트렌드 데이터 저장: {output_file}")
            return all_trends
        
        return None
    
    def get_top_gainers_losers(self, trends_df, top_n=10):
        """상위 상승자/하락자 분석"""
        if trends_df is None or trends_df.empty:
            return None, None
        
        # 최신 주차 데이터만 사용
        latest_week = trends_df['current_week'].max()
        latest_trends = trends_df[trends_df['current_week'] == latest_week].copy()
        
        # 상위 상승자 (변화율 기준)
        top_gainers = latest_trends.nlargest(top_n, 'change_rate')
        
        # 상위 하락자 (변화율 기준)
        top_losers = latest_trends.nsmallest(top_n, 'change_rate')
        
        return top_gainers, top_losers
    
    def generate_weekly_summary(self, trends_df):
        """주간 요약 리포트 생성"""
        if trends_df is None or trends_df.empty:
            return None
        
        # 최신 주차 데이터
        latest_week = trends_df['current_week'].max()
        latest_trends = trends_df[trends_df['current_week'] == latest_week].copy()
        
        summary = {
            'week': latest_week,
            'total_artists': len(latest_trends),
            'avg_score_change': latest_trends['score_change'].mean(),
            'avg_change_rate': latest_trends['change_rate'].mean(),
            'artists_up': len(latest_trends[latest_trends['trend'] == 'up']),
            'artists_down': len(latest_trends[latest_trends['trend'] == 'down']),
            'artists_stable': len(latest_trends[latest_trends['trend'] == 'stable']),
            'max_gain': latest_trends['change_rate'].max(),
            'max_loss': latest_trends['change_rate'].min(),
            'top_gainer': latest_trends.loc[latest_trends['change_rate'].idxmax(), 'artist'],
            'top_loser': latest_trends.loc[latest_trends['change_rate'].idxmin(), 'artist']
        }
        
        # JSON으로 저장
        summary_file = self.analytics_dir / f"weekly_summary_{datetime.now().strftime('%Y%m%d')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        return summary

def main():
    """메인 실행 함수"""
    tracker = WeeklyScoreTracker()
    
    print("🚀 BigC 아티스트 주간 스코어 트렌드 분석 시작")
    
    # 주간 트렌드 생성
    trends_df = tracker.generate_weekly_trends()
    
    if trends_df is not None:
        # 상위 상승자/하락자 분석
        top_gainers, top_losers = tracker.get_top_gainers_losers(trends_df, top_n=10)
        
        print("\n🔥 이번 주 상위 상승자 Top 10:")
        if top_gainers is not None:
            for i, row in top_gainers.iterrows():
                print(f"{top_gainers.index.get_loc(i)+1:2d}. {row['artist']:15s} +{row['change_rate']:6.2f}% ({row['entertainment']})")
        
        print("\n📉 이번 주 상위 하락자 Top 10:")
        if top_losers is not None:
            for i, row in top_losers.iterrows():
                print(f"{top_losers.index.get_loc(i)+1:2d}. {row['artist']:15s} {row['change_rate']:7.2f}% ({row['entertainment']})")
        
        # 주간 요약 생성
        summary = tracker.generate_weekly_summary(trends_df)
        if summary:
            print(f"\n📊 {summary['week']} 주간 요약:")
            print(f"   전체 아티스트: {summary['total_artists']}명")
            print(f"   상승: {summary['artists_up']}명, 하락: {summary['artists_down']}명, 유지: {summary['artists_stable']}명")
            print(f"   평균 변화율: {summary['avg_change_rate']:.2f}%")
            print(f"   최대 상승: {summary['top_gainer']} (+{summary['max_gain']:.2f}%)")
            print(f"   최대 하락: {summary['top_loser']} ({summary['max_loss']:.2f}%)")
    
    print("\n✅ 주간 트렌드 분석 완료!")

if __name__ == "__main__":
    main()