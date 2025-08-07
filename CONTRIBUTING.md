# 기여 가이드 (Contributing Guide)

## 🌳 브랜치 전략 (Git Flow)

이 프로젝트는 **Git Flow** 브랜치 전략을 따릅니다.

### 브랜치 구조

```
main (프로덕션)
├── develop (개발 통합)
    ├── feature/new-crawler (새 기능)
    ├── feature/slack-notification (기능 추가)
    └── hotfix/bug-fix (긴급 수정)
```

### 📋 브랜치 설명

| 브랜치 | 용도 | 설명 |
|--------|------|------|
| `main` | 🚀 **프로덕션** | 실제 서비스되는 안정된 코드 |
| `develop` | 🔧 **개발 통합** | 개발 완료된 기능들이 통합되는 브랜치 |
| `feature/*` | ✨ **새 기능** | 새로운 기능 개발 브랜치 |
| `hotfix/*` | 🚨 **긴급 수정** | 프로덕션 긴급 버그 수정 |
| `release/*` | 📦 **릴리즈** | 배포 준비 브랜치 |

## 🔄 워크플로우

### 1. 새 기능 개발 시

```bash
# develop 브랜치에서 시작
git checkout develop
git pull origin develop

# 새 기능 브랜치 생성
git checkout -b feature/your-feature-name

# 개발 작업...
git add .
git commit -m "feat: 새로운 크롤링 기능 추가"

# 원격에 푸시
git push origin feature/your-feature-name

# GitHub에서 develop으로 Pull Request 생성
```

### 2. 개발 브랜치 → 프로덕션 배포

```bash
# develop에서 release 브랜치 생성
git checkout develop
git checkout -b release/v1.2.0

# 버전 정보 업데이트, 최종 테스트...
git commit -m "chore: version 1.2.0 release"

# main과 develop에 병합
git checkout main
git merge release/v1.2.0
git tag v1.2.0

git checkout develop  
git merge release/v1.2.0

# 브랜치 정리
git branch -d release/v1.2.0
```

### 3. 긴급 버그 수정 시

```bash
# main에서 hotfix 브랜치 생성
git checkout main
git checkout -b hotfix/critical-bug

# 버그 수정...
git commit -m "fix: 크리티컬 버그 수정"

# main과 develop 모두에 병합
git checkout main
git merge hotfix/critical-bug
git tag v1.2.1

git checkout develop
git merge hotfix/critical-bug

# 브랜치 정리  
git branch -d hotfix/critical-bug
```

## 🤖 GitHub Actions 자동화

### Development 환경
- **트리거**: `develop` 브랜치 푸시, 매주 화요일 10시
- **용도**: 개발 테스트 및 검증
- **알림**: Slack으로 테스트 결과 전송

### Production 환경  
- **트리거**: `main` 브랜치, 매주 월요일 9시
- **용도**: 실제 데이터 수집 및 서비스
- **알림**: Slack으로 프로덕션 상태 알림

## 📝 커밋 메시지 규칙

### 커밋 타입
- `feat`: 새로운 기능
- `fix`: 버그 수정  
- `docs`: 문서 수정
- `style`: 코드 포매팅, 세미콜론 누락 등
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가 또는 수정
- `chore`: 빌드 프로세스, 도구 변경 등

### 예시
```bash
feat: Instagram 크롤링 기능 추가
fix: YouTube API 호출 에러 수정
docs: README 설치 가이드 업데이트
refactor: 크롤링 공통 함수 분리
test: Slack 알림 테스트 케이스 추가
chore: 의존성 패키지 업데이트
```

## 🔍 Pull Request 가이드

### PR 생성 전 체크리스트
- [ ] 로컬에서 테스트 완료
- [ ] 코드 스타일 일관성 확인
- [ ] 관련 문서 업데이트
- [ ] 커밋 메시지 규칙 준수

### PR 설명 작성
- 변경사항 명확히 설명
- 관련 이슈 링크
- 테스트 방법 기술
- 스크린샷 첨부 (UI 변경시)

## 🧪 테스트 가이드

### 필수 테스트 항목
- [ ] 크롤링 기능 정상 작동
- [ ] Slack 알림 전송 확인
- [ ] 스케줄러 동작 검증
- [ ] 에러 핸들링 테스트

### 테스트 실행
```bash
# Slack 알림 테스트
python3 utils/slack_notifications.py

# 스케줄러 테스트  
python3 scheduler.py daily

# 전체 워크플로우 테스트
python3 scheduler.py weekly
```

## 🛠️ 개발 환경 설정

### 1. 리포지토리 클론
```bash
git clone https://github.com/Haryy-Park00/kpop-artist-scoring.git
cd kpop-artist-scoring
```

### 2. 브랜치 설정
```bash
# develop 브랜치로 전환
git checkout develop
git pull origin develop
```

### 3. 환경 설정
```bash
# 의존성 설치
pip3 install -r requirements.txt

# 환경변수 설정 (.env 파일 생성)
cp .env.example .env
# .env 파일 편집하여 API 키 등 설정
```

### 4. 첫 테스트
```bash
# 개발 환경 테스트
python3 scheduler.py daily
```

## 🚨 주의사항

### 보안
- `.env` 파일은 절대 커밋하지 마세요
- API 키나 비밀번호는 GitHub Secrets 사용
- 개인정보가 포함된 데이터는 제외

### 코드 품질
- 일관된 코딩 스타일 유지
- 적절한 주석과 문서화
- 에러 핸들링 필수 구현

### 협업
- 큰 변경사항은 사전 논의
- 코드 리뷰 적극 참여
- 이슈나 PR에서 소통

---

## 📞 문의

궁금한 점이 있으시면 이슈를 생성하거나 PR에 댓글을 남겨주세요!

**Happy Coding! 🎵✨**