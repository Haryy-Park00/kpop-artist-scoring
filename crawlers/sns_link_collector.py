#!/usr/bin/env python3
"""
1단계: 아티스트별 SNS 링크 수집기 (인스타그램, 유튜브, 트위터)
"""
import os
import sys
import time
import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.path_utils import get_path
from utils.common_functions import get_current_week_info, save_dataframe_csv
from config import CHROME_DRIVER_PATH


def setup_chrome_driver():
    """Chrome 드라이버 설정"""
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"Chrome 드라이버 설정 실패: {e}")
        return None


def find_sns_links_for_artist(driver, artist_name):
    """네이버 검색으로 아티스트의 SNS 링크들 찾기"""
    search_url = f'https://search.naver.com/search.naver?where=nexearch&query={artist_name}+프로필'
    
    print(f"🔍 검색 중: {artist_name}")
    driver.get(search_url)
    time.sleep(3)
    
    # 결과 저장용
    sns_links = {
        'artist_name': artist_name,
        'instagram_link': None,
        'youtube_link': None,
        'twitter_link': None
    }
    
    try:
        # 프로필 영역 찾기
        profile = driver.find_element(By.CLASS_NAME, "cm_content_area._cm_content_area_profile")
        
        # 더보기 버튼 클릭 시도
        try:
            more_btn = profile.find_element(By.CLASS_NAME, "area_button_arrow")
            more_btn.click()
            time.sleep(1)
        except NoSuchElementException:
            pass
        
        # 1. 인스타그램 링크 찾기
        instagram_selectors = [
            "a[href^='https://www.instagram.com/']",
            "a[href^='https://instagram.com/']"
        ]
        
        for selector in instagram_selectors:
            try:
                insta_element = profile.find_element(By.CSS_SELECTOR, selector)
                sns_links['instagram_link'] = insta_element.get_attribute('href')
                print(f"  📸 인스타그램: {sns_links['instagram_link']}")
                break
            except NoSuchElementException:
                continue
        
        # 2. 유튜브 링크 찾기
        youtube_selectors = [
            "a[href^='https://www.youtube.com/']",
            "a[href^='https://www.youtube.com/channel/']",
            "a[href^='https://www.youtube.com/@']",
            "a[href^='https://youtube.com/']"
        ]
        
        for selector in youtube_selectors:
            try:
                youtube_element = profile.find_element(By.CSS_SELECTOR, selector)
                sns_links['youtube_link'] = youtube_element.get_attribute('href')
                print(f"  🎵 유튜브: {sns_links['youtube_link']}")
                break
            except NoSuchElementException:
                continue
        
        # 3. 트위터 링크 찾기
        twitter_selectors = [
            "a[href^='https://twitter.com/']",
            "a[href^='https://www.twitter.com/']",
            "a[href^='https://x.com/']",
            "a[href^='https://www.x.com/']"
        ]
        
        for selector in twitter_selectors:
            try:
                twitter_element = profile.find_element(By.CSS_SELECTOR, selector)
                sns_links['twitter_link'] = twitter_element.get_attribute('href')
                print(f"  🐦 트위터: {sns_links['twitter_link']}")
                break
            except NoSuchElementException:
                continue
        
        # 찾은 링크 개수 출력
        found_count = sum(1 for link in [sns_links['instagram_link'], sns_links['youtube_link'], sns_links['twitter_link']] if link)
        print(f"  ✅ 총 {found_count}개 링크 발견")
        
        if found_count == 0:
            print(f"  ❌ SNS 링크 없음")
            
    except NoSuchElementException:
        print(f"  ❌ 프로필 정보 없음")
    
    return sns_links


def collect_all_sns_links(artist_names):
    """모든 아티스트의 SNS 링크 수집"""
    driver = setup_chrome_driver()
    if not driver:
        print("Chrome 드라이버를 설정할 수 없습니다.")
        return None
    
    all_sns_data = []
    
    try:
        for i, artist in enumerate(artist_names, 1):
            print(f"\n[{i}/{len(artist_names)}] 처리 중...")
            
            try:
                sns_data = find_sns_links_for_artist(driver, artist)
                all_sns_data.append(sns_data)
                
                # 요청 간격 (네이버 차단 방지)
                time.sleep(2)
                
            except Exception as e:
                print(f"  ❌ 오류 발생 ({artist}): {e}")
                # 오류가 있어도 빈 데이터라도 추가
                all_sns_data.append({
                    'artist_name': artist,
                    'instagram_link': None,
                    'youtube_link': None,
                    'twitter_link': None
                })
                continue
    
    finally:
        driver.quit()
    
    return pd.DataFrame(all_sns_data)


def main():
    """메인 실행 함수"""
    print("🎵 아티스트 SNS 링크 수집기 시작")
    print("=" * 50)
    
    # 아티스트 리스트 로드
    try:
        artist_folder = get_path("data/artist_list")
        import glob
        files = glob.glob(str(artist_folder / "*한터차트*월드*.csv"))
        
        if not files:
            print("❌ 아티스트 리스트 파일을 찾을 수 없습니다.")
            return
        
        latest_file = max(files)
        print(f"📁 아티스트 리스트 로드: {latest_file}")
        
        artist_df = pd.read_csv(latest_file)
        if '아티스트명' not in artist_df.columns:
            print("❌ '아티스트명' 컬럼을 찾을 수 없습니다.")
            return
        
        artist_names = artist_df['아티스트명'].unique().tolist()
        print(f"📊 총 {len(artist_names)}명의 아티스트")
        
        # SNS 링크 수집
        print(f"\n🚀 SNS 링크 수집 시작...")
        sns_df = collect_all_sns_links(artist_names)
        
        if sns_df is None or sns_df.empty:
            print("❌ 수집된 데이터가 없습니다.")
            return
        
        # 년도/주차 정보 추가
        year, week_number, _ = get_current_week_info()
        sns_df['수집년도'] = year
        sns_df['수집주차'] = week_number
        sns_df['수집일시'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 결과 저장
        output_path = get_path(f"data/sns_links/{year}년_{week_number}주차_SNS링크수집.csv")
        output_path.parent.mkdir(exist_ok=True)
        save_dataframe_csv(sns_df, output_path)
        
        # 결과 요약
        print(f"\n✅ 수집 완료! 저장 위치: {output_path}")
        print("\n📊 수집 결과 요약:")
        
        total_artists = len(sns_df)
        instagram_count = sns_df['instagram_link'].notna().sum()
        youtube_count = sns_df['youtube_link'].notna().sum()
        twitter_count = sns_df['twitter_link'].notna().sum()
        
        print(f"- 수집 년도/주차: {year}년 {week_number}주차")
        print(f"- 총 아티스트: {total_artists}명")
        print(f"- 인스타그램 링크: {instagram_count}개 ({instagram_count/total_artists*100:.1f}%)")
        print(f"- 유튜브 링크: {youtube_count}개 ({youtube_count/total_artists*100:.1f}%)")
        print(f"- 트위터 링크: {twitter_count}개 ({twitter_count/total_artists*100:.1f}%)")
        
        # 샘플 결과 출력
        print(f"\n📋 샘플 결과 (처음 5개):")
        sample_df = sns_df.head(5)
        for _, row in sample_df.iterrows():
            print(f"\n🎤 {row['artist_name']}")
            if pd.notna(row['instagram_link']):
                print(f"  📸 인스타그램: {row['instagram_link']}")
            if pd.notna(row['youtube_link']):
                print(f"  🎵 유튜브: {row['youtube_link']}")
            if pd.notna(row['twitter_link']):
                print(f"  🐦 트위터: {row['twitter_link']}")
            if pd.isna(row['instagram_link']) and pd.isna(row['youtube_link']) and pd.isna(row['twitter_link']):
                print(f"  ❌ SNS 링크 없음")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()