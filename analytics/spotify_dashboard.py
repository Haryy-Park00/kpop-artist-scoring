"""
Spotify 데이터 분석 대시보드
주간 데이터의 시각화 및 분석 기능 제공
"""
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
from datetime import datetime, timedelta

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'  # macOS
plt.rcParams['axes.unicode_minus'] = False

sys.path.append(str(Path(__file__).parent.parent))

class SpotifyDashboard:
    def __init__(self):
        self.db_path = Path("data/database/spotify_weekly.db")
        
    def get_connection(self):
        """데이터베이스 연결"""
        return sqlite3.connect(self.db_path)
    
    def generate_weekly_report(self, weeks=4):
        """주간 리포트 생성"""
        conn = self.get_connection()
        
        # 기본 통계
        stats_query = '''
            SELECT 
                year, week, collection_date,
                COUNT(*) as artist_count,
                AVG(followers) as avg_followers,
                MAX(followers) as max_followers,
                MIN(followers) as min_followers,
                AVG(popularity) as avg_popularity
            FROM weekly_data 
            WHERE collection_date >= date('now', '-{} weeks')
            GROUP BY year, week, collection_date
            ORDER BY collection_date DESC
        '''.format(weeks)
        
        stats_df = pd.read_sql_query(stats_query, conn)
        
        # 상위 성장 아티스트
        growth_query = '''
            SELECT 
                a.artist_name,
                h.follower_change,
                h.popularity_change,
                h.collection_date,
                h.followers
            FROM follower_history h
            JOIN artists_master a ON h.artist_id = a.artist_id
            WHERE h.collection_date >= date('now', '-1 week')
            AND h.follower_change > 0
            ORDER BY h.follower_change DESC
            LIMIT 10
        '''
        
        growth_df = pd.read_sql_query(growth_query, conn)
        
        # 하락 아티스트
        decline_query = '''
            SELECT 
                a.artist_name,
                h.follower_change,
                h.popularity_change,
                h.collection_date,
                h.followers
            FROM follower_history h
            JOIN artists_master a ON h.artist_id = a.artist_id
            WHERE h.collection_date >= date('now', '-1 week')
            AND h.follower_change < 0
            ORDER BY h.follower_change ASC
            LIMIT 10
        '''
        
        decline_df = pd.read_sql_query(decline_query, conn)
        conn.close()
        
        return {
            'stats': stats_df,
            'growth': growth_df,
            'decline': decline_df
        }
    
    def plot_follower_trends(self, artist_names, weeks=8):
        """아티스트 팔로워 트렌드 시각화"""
        conn = self.get_connection()
        
        plt.figure(figsize=(12, 8))
        
        for artist_name in artist_names:
            query = '''
                SELECT 
                    h.collection_date,
                    h.followers,
                    a.artist_name
                FROM follower_history h
                JOIN artists_master a ON h.artist_id = a.artist_id
                WHERE a.artist_name LIKE ?
                AND h.collection_date >= date('now', '-{} weeks')
                ORDER BY h.collection_date
            '''.format(weeks)
            
            df = pd.read_sql_query(query, conn, params=(f'%{artist_name}%',))
            
            if not df.empty:
                df['collection_date'] = pd.to_datetime(df['collection_date'])
                plt.plot(df['collection_date'], df['followers'], 
                        marker='o', linewidth=2, label=df['artist_name'].iloc[0])
        
        plt.title(f'아티스트 팔로워 트렌드 (최근 {weeks}주)', fontsize=16, fontweight='bold')
        plt.xlabel('날짜', fontsize=12)
        plt.ylabel('팔로워 수', fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 이미지 저장
        save_path = Path("data/analytics/follower_trends.png")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        conn.close()
        return str(save_path)
    
    def plot_popularity_distribution(self):
        """인기도 분포 시각화"""
        conn = self.get_connection()
        
        query = '''
            SELECT popularity, followers
            FROM weekly_data 
            WHERE collection_date = (SELECT MAX(collection_date) FROM weekly_data)
            AND popularity IS NOT NULL
            AND followers IS NOT NULL
        '''
        
        df = pd.read_sql_query(query, conn)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 인기도 히스토그램
        ax1.hist(df['popularity'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax1.set_title('인기도 분포', fontsize=14, fontweight='bold')
        ax1.set_xlabel('인기도 점수')
        ax1.set_ylabel('아티스트 수')
        ax1.grid(True, alpha=0.3)
        
        # 팔로워 vs 인기도 산점도
        ax2.scatter(df['followers'], df['popularity'], alpha=0.6, color='coral')
        ax2.set_title('팔로워 수 vs 인기도', fontsize=14, fontweight='bold')
        ax2.set_xlabel('팔로워 수')
        ax2.set_ylabel('인기도 점수')
        ax2.set_xscale('log')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 이미지 저장
        save_path = Path("data/analytics/popularity_distribution.png")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        conn.close()
        return str(save_path)
    
    def generate_growth_ranking(self, period='week'):
        """성장률 랭킹 생성"""
        conn = self.get_connection()
        
        if period == 'week':
            time_filter = "date('now', '-1 week')"
        elif period == 'month':
            time_filter = "date('now', '-1 month')"
        else:
            time_filter = "date('now', '-1 week')"
        
        query = f'''
            SELECT 
                a.artist_name,
                h.followers,
                h.follower_change,
                h.popularity,
                h.popularity_change,
                ROUND((CAST(h.follower_change AS REAL) / CAST(h.followers - h.follower_change AS REAL)) * 100, 2) as growth_rate
            FROM follower_history h
            JOIN artists_master a ON h.artist_id = a.artist_id
            WHERE h.collection_date >= {time_filter}
            AND h.followers > 1000  -- 최소 팔로워 수 필터
            AND h.follower_change != 0
            ORDER BY growth_rate DESC
            LIMIT 20
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def export_summary_to_csv(self):
        """요약 데이터를 CSV로 내보내기"""
        report = self.generate_weekly_report()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 통계 요약
        stats_path = Path(f"data/analytics/weekly_stats_{timestamp}.csv")
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        report['stats'].to_csv(stats_path, index=False, encoding='utf-8-sig')
        
        # 성장 랭킹
        growth_path = Path(f"data/analytics/growth_ranking_{timestamp}.csv")
        report['growth'].to_csv(growth_path, index=False, encoding='utf-8-sig')
        
        # 하락 랭킹
        decline_path = Path(f"data/analytics/decline_ranking_{timestamp}.csv")
        report['decline'].to_csv(decline_path, index=False, encoding='utf-8-sig')
        
        return {
            'stats': str(stats_path),
            'growth': str(growth_path),
            'decline': str(decline_path)
        }

def main():
    """메인 함수"""
    dashboard = SpotifyDashboard()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "report":
            # 주간 리포트 생성
            report = dashboard.generate_weekly_report()
            
            print("📊 주간 통계 요약:")
            print(report['stats'].to_string(index=False))
            print("\n📈 상위 성장 아티스트:")
            print(report['growth'].to_string(index=False))
            print("\n📉 팔로워 하락 아티스트:")
            print(report['decline'].to_string(index=False))
        
        elif command == "trends":
            # 아티스트 트렌드 시각화
            if len(sys.argv) > 2:
                artists = sys.argv[2].split(',')
                image_path = dashboard.plot_follower_trends(artists)
                print(f"📈 트렌드 차트 저장됨: {image_path}")
            else:
                print("사용법: python spotify_dashboard.py trends <아티스트1,아티스트2,...>")
        
        elif command == "distribution":
            # 인기도 분포 시각화
            image_path = dashboard.plot_popularity_distribution()
            print(f"📊 분포 차트 저장됨: {image_path}")
        
        elif command == "ranking":
            # 성장률 랭킹
            period = sys.argv[2] if len(sys.argv) > 2 else 'week'
            ranking = dashboard.generate_growth_ranking(period)
            print(f"🏆 {period} 성장률 랭킹:")
            print(ranking.to_string(index=False))
        
        elif command == "export":
            # CSV 내보내기
            files = dashboard.export_summary_to_csv()
            print("📁 CSV 파일 내보내기 완료:")
            for key, path in files.items():
                print(f"   {key}: {path}")
        
        else:
            print_usage()
    else:
        print_usage()

def print_usage():
    """사용법 출력"""
    print("Spotify 데이터 분석 대시보드")
    print("\n사용법:")
    print("  python spotify_dashboard.py report                    # 주간 리포트")
    print("  python spotify_dashboard.py trends <아티스트1,아티스트2> # 트렌드 시각화")
    print("  python spotify_dashboard.py distribution             # 인기도 분포")
    print("  python spotify_dashboard.py ranking [week|month]     # 성장률 랭킹")
    print("  python spotify_dashboard.py export                   # CSV 내보내기")

if __name__ == "__main__":
    main()