#!/usr/bin/env python3
"""
2단계: 수집된 SNS 링크로 실제 데이터 크롤링 (CSV URL 직접 사용)
"""
import os
import sys
import time
import re
import glob
from pathlib import Path

import pandas as pd
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

# 프로젝트 루트 추가
sys.path.append(str(Path(__file__).parent.parent))

from utils.path_utils import get_path
from utils.common_functions import get_current_week_info, save_dataframe_csv, process_numeric_string
from utils.selenium_base import ChromeDriverFactory
from utils.logging_config import get_project_logger
from utils.error_handling import with_retry
from config import get_config

logger = get_project_logger(__name__)


def _close_instagram_popups(driver):
    """인스타그램 팝업 닫기 헬퍼 함수"""
    try:
        popup_boxes = driver.find_elements(By.CLASS_NAME, 'x6s0dn4.x78zum5.xdt5ytf.xl56j7k')
        for box in popup_boxes:
            try:
                close_button = box.find_element(
                    By.XPATH,
                    './/svg[@aria-label="닫기" and contains(@class, "x1lliihq") and contains(@class, "x1n2onr6") and contains(@class, "x1roi4f4")]'
                )
                close_button.click()
            except NoSuchElementException:
                pass
    except NoSuchElementException:
        pass


def _try_alternative_instagram_selector(driver):
    """대체 인스타그램 셀렉터로 팔로워 수 추출 시도"""
    try:
        follower_element = driver.find_element(
            By.CLASS_NAME,
            "html-span.xdj266r.x11i5rnm.xat24cr.x1mh8g0r."
            "xexx8yu.x4uap5.x18d9i69.xkhd6sd.x1hl2dhg."
            "x16tdsg8.x1vvkbs"
        )
        follower_text = follower_element.text
        print(f"    📸 인스타그램 대체 텍스트: {follower_text}")
        follower_count = process_numeric_string(follower_text) if follower_text else 0
        print(f"    ✅ 인스타그램 팔로워 수: {follower_count:,}")
        return follower_count
    except NoSuchElementException:
        return 0


@with_retry(max_attempts=3)
def setup_chrome_driver():
    """Chrome 드라이버 설정 - ChromeDriverFactory 사용"""
    try:
        driver = ChromeDriverFactory.create_chrome_driver(headless=False, use_stealth=True)
        logger.info("Chrome 드라이버 설정 성공")
        return driver
    except Exception as e:
        logger.error(f"Chrome 드라이버 설정 실패: {e}")
        return None


@with_retry(max_attempts=2)
def login_instagram(driver):
    """인스타그램 로그인 처리"""
    try:
        logger.info('인스타그램 로그인 시도...')
        
        # 현재 URL이 로그인 페이지인지 확인
        current_url = driver.current_url
        if 'accounts/login' not in current_url:
            logger.info(f'현재 URL: {current_url}')
            logger.info('로그인 페이지가 아닙니다. 건너뜁니다.')
            return True

        instagram_id = os.getenv('INSTAGRAM_ID')
        instagram_pw = os.getenv('INSTAGRAM_PASSWORD')
        
        if not instagram_id or not instagram_pw:
            logger.error('인스타그램 로그인 정보가 환경변수에 설정되지 않았습니다.')
            return False
        
        username_input = driver.find_element(By.CSS_SELECTOR, "input[aria-label='전화번호, 사용자 이름 또는 이메일']")
        username_input.send_keys(instagram_id)
        
        password_input = driver.find_element(By.CSS_SELECTOR, "input[aria-label='비밀번호']")
        password_input.send_keys(instagram_pw)
                
        time.sleep(2)
        
        # 로그인 버튼 클릭
        login_button = driver.find_element(By.XPATH, "//button[./div[contains(text(), '로그인')]]")
    
        login_button.click()
        time.sleep(10)
        print('✅ 인스타그램 로그인 완료')
        return True

    except NoSuchElementException:
        print('❌ 인스타그램 로그인 실패(요소 미발견). 패스합니다.')
        return False
    except Exception as e:
        print(f'❌ 인스타그램 로그인 오류: {e}')
        return False


def get_youtube_data_via_api(youtube_links):
    """YouTube API로 데이터 수집"""
    youtube_data = {}
    
    # API 키 확인
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("⚠️ YOUTUBE_API_KEY가 설정되지 않았습니다. YouTube 데이터는 건너뜁니다.")
        return youtube_data
    
    try:
        from api_clients.youtube_api import YouTubeAPIClient
        client = YouTubeAPIClient(api_key)
        
        # URL과 아티스트명 쌍 생성
        url_artist_pairs = [(url, artist) for artist, url in youtube_links.items() if pd.notna(url)]
        
        if url_artist_pairs:
            print(f"🎵 YouTube API로 {len(url_artist_pairs)}개 채널 데이터 수집 중...")
            youtube_df = client.get_channels_from_url_list(url_artist_pairs)
            
            # 딕셔너리로 변환
            for _, row in youtube_df.iterrows():
                youtube_data[row['artist_name']] = {
                    'subscriber_count': row.get('subscriber_count', 0),
                    'view_count': row.get('view_count', 0),
                    'video_count': row.get('video_count', 0),
                    'channel_title': row.get('channel_title', '')
                }
        
    except Exception as e:
        
        print(f"❌ YouTube API 오류: {e}")
    
    return youtube_data


@with_retry(max_attempts=3)
def get_instagram_followers(driver, instagram_url):
    """인스타그램 팔로워 수 크롤링 (CSV에서 가져온 URL 직접 사용)"""
    if pd.isna(instagram_url):
        return 0
    
    instagram_follower_num = 0
    
    try:
        print(f"  📸 인스타그램 접속: {instagram_url}")
        
        # 현재 탭에서 인스타그램 URL로 이동
        driver.get(instagram_url)
        time.sleep(5)
        
        # 로그인 페이지로 리다이렉트되었는지 확인하고 자동 로그인
        if 'accounts/login' in driver.current_url:
            print(f"🔐 로그인 페이지로 리다이렉트됨. 자동 로그인 시도...")
            login_success = login_instagram(driver)
            if login_success:
                # 로그인 후 원래 URL로 다시 이동
                driver.get(instagram_url)
                time.sleep(5)

        # 팝업(알림, 쿠키창 등) 닫기
        _close_instagram_popups(driver)

        # 팔로워 수 추출
        try:
            main_boxes = driver.find_element(By.CLASS_NAME, 'x78zum5.x1q0g3np.xieb3on')
            three_lists = main_boxes.find_elements(By.CLASS_NAME, 'xl565be.x11gldyt.x1pwwqoy.x1j53mea')
            row_text = three_lists[1].text
            print(f"    📸 인스타그램 raw 텍스트: {row_text}")
            
            # "팔로워 40.2만" 형태에서 숫자 부분만 추출
            follower_match = re.search(r'팔로워\s*([\d.]+[만천백억KM]?)', row_text)
            if follower_match:
                follower_text = follower_match.group(1)  # "40.2만" 추출
                instagram_follower_num = process_numeric_string(follower_text)
                print(f"    ✅ 인스타그램 팔로워 수: {follower_text} -> {instagram_follower_num:,}")
            else:
                # "Followers" 영어 버전도 시도
                follower_match = re.search(r'Followers\s*([\d.]+[MK만천백억]?)', row_text, re.IGNORECASE)
                if follower_match:
                    follower_text = follower_match.group(1)
                    instagram_follower_num = process_numeric_string(follower_text)
                    print(f"    ✅ 인스타그램 팔로워 수: {follower_text} -> {instagram_follower_num:,}")
                else:
                    # 패턴 매칭 실패시 0
                    print(f"    ❌ 인스타그램 팔로워 수 패턴 매칭 실패")
                    instagram_follower_num = 0
        except NoSuchElementException:
            # 대체 위치 시도
            instagram_follower_num = _try_alternative_instagram_selector(driver)
            if instagram_follower_num == 0:
                print(f"    ❌ 인스타그램 팔로워 수 찾지 못함")


    except Exception as e:
        print(f"    ❌ 인스타그램 크롤링 오류: {e}")

    return instagram_follower_num


@with_retry(max_attempts=2)
def get_twitter_followers(driver, twitter_url):
    """트위터/X 팔로워 수 크롤링 (CSV에서 가져온 URL 직접 사용)"""
    if pd.isna(twitter_url):
        return 0
    
    twitter_follower_num = 0
    
    try:
        print(f"트위터 접속: {twitter_url}")
        
        # 새 탭에서 트위터 열기
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(twitter_url)
        time.sleep(10)  # 트위터 로딩 대기

        try:
            tw_follower_text = driver.find_element(
                By.XPATH,
                "/html/body/div[1]/div/div/div[2]/main/div/div/div/div[1]/"
                "div/div[3]/div/div/div/div/div[5]/div[2]/a/span[1]/span"
            ).text
            print(f"트위터 raw 텍스트: {tw_follower_text}")
            
            # 트위터 팔로워 수 처리 (이미 숫자만 있을 가능성이 높음)
            if tw_follower_text:
                twitter_follower_num = process_numeric_string(tw_follower_text)
                print(f"트위터 팔로워 수: {tw_follower_text} -> {twitter_follower_num:,}")
            else:
                twitter_follower_num = 0
        except NoSuchElementException:
            print(f"트위터 팔로워 수 찾지 못함")
            twitter_follower_num = 0

        # 탭 닫고 원래 탭으로 복귀
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    except Exception as e:
        print(f"트위터 크롤링 오류: {e}")
        # 오류 발생시 탭 정리
        try:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
        except Exception:
            pass

    return twitter_follower_num


def collect_sns_data(sns_links_df):
    """SNS 링크로부터 실제 데이터 수집"""
    driver = setup_chrome_driver()
    if not driver:
        print("Chrome 드라이버를 설정할 수 없습니다.")
        return None
    
    # YouTube API 데이터 수집 (한 번에)
    youtube_links = sns_links_df.set_index('artist_name')['youtube_link'].to_dict()
    youtube_data = get_youtube_data_via_api(youtube_links)
    
    # 결과 저장용 리스트
    all_data = []
    
    try:
        for i, row in sns_links_df.iterrows():
            artist_name = row['artist_name']
            print(f"\n[{i+1}/{len(sns_links_df)}] 🎤 {artist_name} 데이터 수집 중...")
            
            # 기본 데이터 구조
            artist_data = {
                'artist_name': artist_name,
                'instagram_link': row.get('instagram_link'),
                'youtube_link': row.get('youtube_link'),
                'twitter_link': row.get('twitter_link'),
                'instagram_followers': 0,
                'youtube_subscribers': 0,
                'twitter_followers': 0,
                'youtube_views': 0,
                'youtube_videos': 0,

            }
            
            # YouTube 데이터 
            if artist_name in youtube_data:
                yt_data = youtube_data[artist_name]
                artist_data['youtube_subscribers'] = yt_data.get('subscriber_count', 0)
                artist_data['youtube_views'] = yt_data.get('view_count', 0)
                artist_data['youtube_videos'] = yt_data.get('video_count', 0)
                print(f"YouTube: 구독자 {artist_data['youtube_subscribers']:,}명")
            
            # 인스타그램 크롤링 (URL 직접 사용)
            if pd.notna(row.get('instagram_link')):
                try:
                    artist_data['instagram_followers'] = get_instagram_followers(driver, row['instagram_link'])
                    time.sleep(3)  # 요청 간격
                except Exception as e:
                    print(f"    ❌ 인스타그램 크롤링 실패: {e}")
                    artist_data['instagram_followers'] = 0
            
            # 트위터 크롤링 (URL 직접 사용)
            if pd.notna(row.get('twitter_link')):
                try:
                    artist_data['twitter_followers'] = get_twitter_followers(driver, row['twitter_link'])
                    time.sleep(3)  # 요청 간격
                except Exception as e:
                    print(f"    ❌ 트위터 크롤링 실패: {e}")
                    artist_data['twitter_followers'] = 0
            
            all_data.append(artist_data)
            
            # 진행 상황 출력
            total_followers = artist_data['instagram_followers'] + artist_data['youtube_subscribers'] + artist_data['twitter_followers']
            print(f"  📊 총 팔로워: {total_followers:,}명")
    
    finally:
        driver.quit()
    
    return pd.DataFrame(all_data)


def main():
    """메인 실행 함수"""
    print("📊 SNS 데이터 수집기 (2단계) 시작")
    print("=" * 50)
    
    # 1단계에서 생성된 링크 파일 로드 (최신 파일 우선)
    try:
        data_folder = get_path("data/sns_links")
        files = glob.glob(str(data_folder / "*SNS링크수집*.csv"))
        
        if not files:
            print("❌ SNS 링크 파일을 찾을 수 없습니다.")
            print("먼저 sns_link_collector.py를 실행하세요.")
            print(f"📁 검색 경로: {data_folder}")
            return
        
        # 파일을 수정 시간 기준으로 정렬하여 최신 파일 선택
        files_with_time = [(f, os.path.getmtime(f)) for f in files]
        files_with_time.sort(key=lambda x: x[1], reverse=True)
        latest_file = files_with_time[0][0]
        
        print(f"📁 발견된 SNS 링크 파일 {len(files)}개:")
        for i, (file_path, mod_time) in enumerate(files_with_time[:3]):  # 최신 3개만 표시
            file_name = os.path.basename(file_path)
            mod_date = pd.Timestamp.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M')
            mark = "✅ [최신]" if i == 0 else f"   [{i+1}]"
            print(f"  {mark} {file_name} ({mod_date})")
        
        if len(files) > 3:
            print(f"  ... 외 {len(files)-3}개 파일")
        
        print(f"\n📂 선택된 파일: {os.path.basename(latest_file)}")
        
        sns_links_df = pd.read_csv(latest_file)
        print(f"📊 총 {len(sns_links_df)}명의 아티스트 링크 발견")
        
        # 링크 통계
        instagram_count = sns_links_df['instagram_link'].notna().sum()
        youtube_count = sns_links_df['youtube_link'].notna().sum()
        twitter_count = sns_links_df['twitter_link'].notna().sum()
        
        print(f"  📸 인스타그램: {instagram_count}개")
        print(f"  🎵 유튜브: {youtube_count}개")
        print(f"  🐦 트위터: {twitter_count}개")
        
        # 데이터 수집
        print(f"\n🚀 SNS 데이터 수집 시작...")
        sns_data_df = collect_sns_data(sns_links_df)
        
        if sns_data_df is None or sns_data_df.empty:
            print("❌ 수집된 데이터가 없습니다.")
            return
        
        # 년도/주차 정보 추가
        year, week_number, _ = get_current_week_info()
        sns_data_df['수집년도'] = year
        sns_data_df['수집주차'] = week_number
        sns_data_df['수집일시'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 결과 저장
        output_path = get_path(f"data/follower/{year}년_{week_number}주차_SNS데이터수집.csv")
        save_dataframe_csv(sns_data_df, output_path)
        
        # 결과 요약
        print(f"\n✅ 데이터 수집 완료! 저장 위치: {output_path}")
        print("\n📊 수집 결과 요약:")
        
        total_instagram = sns_data_df['instagram_followers'].sum()
        total_youtube = sns_data_df['youtube_subscribers'].sum()
        total_twitter = sns_data_df['twitter_followers'].sum()
        
        print(f"- 수집 년도/주차: {year}년 {week_number}주차")
        print(f"- 총 인스타그램 팔로워: {total_instagram:,}명")
        print(f"- 총 유튜브 구독자: {total_youtube:,}명")
        print(f"- 총 트위터 팔로워: {total_twitter:,}명")
        print(f"- 전체 합계: {total_instagram + total_youtube + total_twitter:,}명")
        
        # Top 5 출력
        print(f"\n🏆 상위 5명 (총 팔로워 기준):")
        sns_data_df['total_followers'] = (sns_data_df['instagram_followers'] + 
                                         sns_data_df['youtube_subscribers'] + 
                                         sns_data_df['twitter_followers'])
        
        top_5 = sns_data_df.nlargest(5, 'total_followers')
        for _, row in top_5.iterrows():
            print(f"  🎤 {row['artist_name']}: {row['total_followers']:,}명")
            if row['instagram_followers'] > 0:
                print(f"    📸 인스타그램: {row['instagram_followers']:,}")
            if row['youtube_subscribers'] > 0:
                print(f"    🎵 유튜브: {row['youtube_subscribers']:,}")
            if row['twitter_followers'] > 0:
                print(f"    🐦 트위터: {row['twitter_followers']:,}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()