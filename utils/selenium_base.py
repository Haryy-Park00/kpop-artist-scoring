"""
Selenium 크롤링을 위한 공통 베이스 클래스 및 Chrome 드라이버 팩토리
"""
import time
import logging
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from config import get_config, CHROME_DRIVER_PATH
from utils.error_handling import with_retry, handle_selenium_error
from utils.logging_config import get_project_logger

logger = get_project_logger(__name__)


class ChromeDriverFactory:
    """Chrome 드라이버 생성 팩토리"""
    
    @staticmethod
    def create_chrome_driver(headless: bool = True, window_size: tuple = (1920, 1080), 
                           use_stealth: bool = True) -> webdriver.Chrome:
        """
        표준 Chrome 드라이버 생성
        
        Args:
            headless: 헤드리스 모드 여부
            window_size: 브라우저 창 크기
            use_stealth: 탐지 방지 설정 사용 여부
        
        Returns:
            설정된 Chrome 드라이버
        """
        chrome_config = get_config('chrome')
        crawling_config = get_config('crawling')
        
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument('--headless=new')  # 새로운 헤드리스 모드
            
        chrome_options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')
        
        # 기본 Chrome 옵션 적용
        for option in chrome_config.get('options', []):
            chrome_options.add_argument(option)
        
        if use_stealth:
            # 탐지 방지 옵션
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins-discovery")
        
        try:
            # 드라이버 경로 설정
            driver_path = chrome_config.get('path', CHROME_DRIVER_PATH)
            
            if driver_path and driver_path != '/usr/local/bin/chromedriver':
                service = Service(driver_path)
            else:
                # WebDriver Manager 사용
                service = Service(ChromeDriverManager().install())
            
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 타임아웃 설정
            driver.implicitly_wait(crawling_config.get('timeout', 30))
            driver.set_page_load_timeout(crawling_config.get('timeout', 30))
            
            # 탐지 방지 스크립트
            if use_stealth:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
            
            logger.info("Chrome 드라이버 초기화 성공")
            return driver
            
        except Exception as e:
            logger.error(f"Chrome 드라이버 생성 실패: {e}")
            raise


class SeleniumBase(ABC):
    """Selenium 크롤러를 위한 베이스 클래스"""
    
    def __init__(self, headless: bool = True, window_size: tuple = (1920, 1080)):
        """
        Args:
            headless: 헤드리스 모드 여부
            window_size: 브라우저 창 크기 (width, height)
        """
        self.driver = None
        self.wait = None
        self.headless = headless
        self.window_size = window_size
        self.crawling_config = get_config('crawling')
        
    def setup_driver(self):
        """WebDriver 초기화"""
        try:
            self.driver = ChromeDriverFactory.create_chrome_driver(
                headless=self.headless,
                window_size=self.window_size,
                use_stealth=True
            )
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("SeleniumBase 드라이버 설정 완료")
        except Exception as e:
            logger.error(f"드라이버 설정 실패: {e}")
            raise
        
    @handle_selenium_error
    def safe_get_text(self, xpath: str, default: str = "") -> str:
        """안전한 텍스트 추출"""
        try:
            element = self.driver.find_element(By.XPATH, xpath)
            text = element.text.strip()
            return text if text else default
        except NoSuchElementException:
            logger.debug(f"요소를 찾을 수 없음: {xpath}")
            return default
            
    @handle_selenium_error
    def safe_click(self, xpath: str, wait_time: float = None) -> bool:
        """안전한 클릭"""
        if wait_time is None:
            wait_time = self.crawling_config.get('page_load_delay', 3)
            
        try:
            element = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            element.click()
            time.sleep(wait_time)
            logger.debug(f"클릭 성공: {xpath}")
            return True
        except (NoSuchElementException, TimeoutException) as e:
            logger.debug(f"클릭 실패 ({xpath}): {e}")
            return False
            
    @handle_selenium_error
    def safe_input(self, xpath: str, text: str, clear: bool = True) -> bool:
        """안전한 텍스트 입력"""
        try:
            element = self.driver.find_element(By.XPATH, xpath)
            if clear:
                element.clear()
            element.send_keys(text)
            logger.debug(f"텍스트 입력 성공: {xpath}")
            return True
        except NoSuchElementException as e:
            logger.debug(f"텍스트 입력 실패 ({xpath}): {e}")
            return False
            
    @handle_selenium_error  
    def wait_for_element(self, xpath: str, timeout: int = 10):
        """요소가 나타날 때까지 대기"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return element
        except TimeoutException:
            logger.debug(f"요소 대기 타임아웃: {xpath}")
            return None
    
    @with_retry(max_attempts=3, delay=2)
    @handle_selenium_error
    def get_page(self, url: str, sleep_time: float = None):
        """페이지 로드"""
        if sleep_time is None:
            sleep_time = self.crawling_config.get('page_load_delay', 3)
            
        logger.info(f"페이지 로드: {url}")
        self.driver.get(url)
        time.sleep(sleep_time)
        
    def close_driver(self):
        """드라이버 종료"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("드라이버 종료 완료")
        except Exception as e:
            logger.error(f"드라이버 종료 중 오류: {e}")
            
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self.setup_driver()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.close_driver()
        
    @abstractmethod
    def crawl(self):
        """크롤링 메인 로직 (하위 클래스에서 구현)"""
        pass


# 편의 함수들
def setup_chrome_driver(headless: bool = True, window_size: tuple = (1920, 1080)) -> webdriver.Chrome:
    """
    간단한 Chrome 드라이버 설정 (기존 코드 호환성용)
    """
    return ChromeDriverFactory.create_chrome_driver(headless=headless, window_size=window_size)


def create_stealth_driver() -> webdriver.Chrome:
    """
    탐지 방지 기능이 강화된 Chrome 드라이버 생성
    """
    return ChromeDriverFactory.create_chrome_driver(headless=True, use_stealth=True)


class HanteoCrawler(SeleniumBase):
    """한터차트 크롤러 예제"""
    
    def __init__(self, chart_type='world'):
        super().__init__()
        self.chart_type = chart_type
        
    def crawl(self):
        """한터차트 크롤링"""
        if self.chart_type == 'world':
            url = 'https://hanteochart.com/chart/world/global/weekly'
        else:
            url = 'https://hanteochart.com/chart/album/weekly'
            
        self.get_page(url)
        
        # 더보기 버튼 클릭
        more_btn_xpath = "//a[contains(@class, 'btn_more')]"
        while self.safe_click(more_btn_xpath):
            time.sleep(1)
            
        # 차트 데이터 수집
        chart_items = self.driver.find_elements(By.CLASS_NAME, "chart_item")
        data = []
        
        for item in chart_items:
            try:
                rank = item.find_element(By.CLASS_NAME, "rank").text
                artist = item.find_element(By.CLASS_NAME, "artist").text
                album = item.find_element(By.CLASS_NAME, "album").text
                sales = item.find_element(By.CLASS_NAME, "sales").text
                
                data.append({
                    "순위": rank,
                    "아티스트명": artist,
                    "앨범명": album,
                    "판매량": sales
                })
            except NoSuchElementException:
                continue
                
        return data


# 사용 예제
if __name__ == "__main__":
    # 컨텍스트 매니저 사용
    with HanteoCrawler() as crawler:
        data = crawler.crawl()
        print(f"수집된 데이터: {len(data)}개")