# 🎵 K-Pop 아티스트 실시간 데이터 수집 및 점수 매기기 대시보드

K-Pop 아티스트의 Spotify 데이터와 SNS 정보를 실시간으로 수집하고, 수동으로 점수를 매길 수 있는 대시보드입니다.

## ✨ 주요 기능

### 🔍 실시간 데이터 수집
- **Spotify API 연동**: 아티스트 검색, 팔로워 수, 인기도 점수 수집
- **SNS 크롤링**: Instagram, YouTube, Twitter 링크 자동 수집
- **자동 점수 계산**: 수집된 데이터 기반 종합 점수 산출

### 📊 데이터 시각화
- 카테고리별 점수 차트
- 평가 히스토리 추적

## 🌳 브랜치 전략

이 프로젝트는 **Git Flow**를 사용합니다:

- **`main`**: 🚀 프로덕션 안정 브랜치 (실제 데이터 수집)
- **`develop`**: 🔧 개발 통합 브랜치 (새로운 기능 테스트)
- **`feature/*`**: ✨ 기능 개발 브랜치

자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

## 🚀 사용 방법

### 1. 환경 설정
```bash
# 저장소 클론
git clone https://github.com/Haryy-Park00/kpop-artist-scoring.git
cd kpop-artist-scoring

# develop 브랜치로 전환 (개발용)
git checkout develop

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (.env 파일)
```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

### 3. 대시보드 실행
```bash
streamlit run dashboard/streamlit_dashboard.py
```

### 4. 아티스트 평가하기
2. "새 아티스트 검색" 선택
3. 아티스트 이름 입력 (예: "ENHYPEN", "NewJeans")
4. "🔍 실시간 데이터 수집" 버튼 클릭
6. "💾 점수 저장"으로 평가 완료

## 📁 프로젝트 구조

```
kpop-artist-scoring/
├── dashboard/
│   └── streamlit_dashboard.py    # 메인 대시보드
├── api_clients/
│   └── spotify_api.py           # Spotify API 클라이언트
├── crawlers/
│   └── sns_link_collector.py    # SNS 링크 크롤러
├── utils/
│   ├── scoring.py               # 점수 계산 로직
│   ├── common_functions.py      # 공통 함수
│   └── path_utils.py           # 경로 유틸리티
└── requirements.txt             # 필요한 패키지
```

## 🛠️ 기술 스택
- **Frontend**: Streamlit
- **Data Visualization**: Plotly
- **APIs**: Spotify Web API
- **Web Scraping**: Selenium
- **Data Processing**: Pandas

## 📈 점수 계산 방식

### 자동 점수 (0-100점)
- Spotify 인기도 (30%)
- Instagram 팔로워 (25%) 
- Spotify 팔로워 (25%)
- Twitter 팔로워 (20%)

## 🎯 사용 예시

```
아티스트: "NewJeans"
🔍 실시간 데이터 수집 결과:
✅ Spotify: NewJeans (5,234,567 팔로워, 인기도: 89)
✅ Instagram 링크 발견
✅ YouTube 링크 발견
📊 자동 점수: 78.5/100
```

## 🔧 개발 환경
- Python 3.9+
- Streamlit 1.28+
- Chrome WebDriver (크롤링용)

## 📄 라이선스
MIT License