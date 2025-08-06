"""
Selenium 크롤링을 위한 공통 베이스 클래스
"""
import time
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from config import SELENIUM_CONFIG


class SeleniumBase(ABC):
    """Selenium 크롤러를 위한 베이스 클래스"""
    
    
    def __init__(self, headless=None, window_size=None):
        """
        Args:
            headless (bool): 헤드리스 모드 여부
            window_size (tuple): 브라우저 창 크기 (width, height)
        """
        self.driver = None
        self.wait = None
        self.headless = headless if headless is not None else SELENIUM_CONFIG['headless']
        self.window_size = window_size if window_size is not None else SELENIUM_CONFIG['window_size']
        
    def setup_driver(self):
        """WebDriver 초기화"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
            
        chrome_options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User-Agent 설정
        chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # WebDriver Manager로 자동 드라이버 관리
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.implicitly_wait(SELENIUM_CONFIG['implicit_wait'])
        self.driver.set_page_load_timeout(SELENIUM_CONFIG['page_load_timeout'])
        
        # automation 관련 속성 제거
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.wait = WebDriverWait(self.driver, 10)
        
    def safe_get_text(self, xpath):
        """안전한 텍스트 추출"""
        try:
            element = self.driver.find_element(By.XPATH, xpath)
            return element.text.strip() if element.text.strip() else None
        except NoSuchElementException:
            return None
            
    def safe_click(self, xpath, wait_time=1):
        """안전한 클릭"""
        try:
            element = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            element.click()
            time.sleep(wait_time)
            return True
        except (NoSuchElementException, TimeoutException):
            return False
            
    def safe_input(self, xpath, text, clear=True):
        """안전한 텍스트 입력"""
        try:
            element = self.driver.find_element(By.XPATH, xpath)
            if clear:
                element.clear()
            element.send_keys(text)
            return True
        except NoSuchElementException:
            return False
            
    def wait_for_element(self, xpath, timeout=10):
        """요소가 나타날 때까지 대기"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return element
        except TimeoutException:
            return None
            
    def get_page(self, url, sleep_time=3):
        """페이지 로드"""
        self.driver.get(url)
        time.sleep(sleep_time)
        
    def close_driver(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            
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