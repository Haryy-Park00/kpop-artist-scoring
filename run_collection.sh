#!/bin/bash

# K-Pop 아티스트 데이터 수집 실행 스크립트
# 사용법: ./run_collection.sh [sns-links|sns-data|full]

set -e  # 오류 시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 루트로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 로그 함수
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 환경 체크
check_environment() {
    log "환경 체크 시작..."
    
    # Python 체크
    if ! command -v python3 &> /dev/null; then
        error "Python3가 설치되지 않았습니다."
        exit 1
    fi
    
    # 가상환경 체크 (선택사항)
    if [[ -z "$VIRTUAL_ENV" ]]; then
        warning "가상환경이 활성화되지 않았습니다."
    fi
    
    # 필수 디렉토리 생성
    mkdir -p data/{sns_links,follower,integrated_social} logs
    
    success "환경 체크 완료"
}

# SNS 링크 수집
collect_sns_links() {
    log "SNS 링크 수집 시작..."
    
    if python3 crawlers/sns_link_collector.py; then
        success "SNS 링크 수집 완료"
        return 0
    else
        error "SNS 링크 수집 실패"
        return 1
    fi
}

# SNS 데이터 수집
collect_sns_data() {
    log "SNS 데이터 수집 시작..."
    
    if python3 crawlers/sns_data_collector.py; then
        success "SNS 데이터 수집 완료"
        return 0
    else
        error "SNS 데이터 수집 실패"
        return 1
    fi
}

# 전체 수집 프로세스
run_full_collection() {
    log "전체 데이터 수집 시작..."
    
    local success_count=0
    local total_tasks=2
    
    # 1. SNS 링크 수집
    if collect_sns_links; then
        ((success_count++))
        
        # 잠시 대기
        log "다음 단계까지 30초 대기..."
        sleep 30
        
        # 2. SNS 데이터 수집
        if collect_sns_data; then
            ((success_count++))
        fi
    fi
    
    # 결과 리포트
    log "수집 완료: $success_count/$total_tasks 성공"
    
    if [ $success_count -eq $total_tasks ]; then
        success "모든 작업이 성공적으로 완료되었습니다!"
        return 0
    else
        error "일부 작업이 실패했습니다. ($((total_tasks - success_count))개 실패)"
        return 1
    fi
}

# 메인 실행
main() {
    echo -e "${BLUE}"
    echo "================================="
    echo "  K-Pop 데이터 수집 스크립트"
    echo "================================="
    echo -e "${NC}"
    
    check_environment
    
    case "${1:-full}" in
        "sns-links")
            collect_sns_links
            ;;
        "sns-data")
            collect_sns_data
            ;;
        "full")
            run_full_collection
            ;;
        *)
            echo "사용법: $0 [sns-links|sns-data|full]"
            echo ""
            echo "옵션:"
            echo "  sns-links  : SNS 링크만 수집"
            echo "  sns-data   : SNS 데이터만 수집 (링크 수집 필요)"
            echo "  full       : 전체 프로세스 실행 (기본값)"
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"