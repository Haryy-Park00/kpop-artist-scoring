from pathlib import Path

def find_project_root(start_path: Path, marker: str = "README.md") -> Path:
    """특정 파일/폴더(marker)를 기준으로 프로젝트 루트를 탐색"""
    current_path = start_path
    while current_path != current_path.parent:  # 루트 디렉토리까지 탐색
        if (current_path / marker).exists():
            return current_path
        current_path = current_path.parent
    raise FileNotFoundError(f"프로젝트 루트 기준 파일 '{marker}'를 찾을 수 없습니다.")

# 프로젝트 루트 경로를 계산
PROJECT_ROOT = find_project_root(Path(__file__).resolve())

def get_path(relative_path: str) -> Path:
    """프로젝트 루트를 기준으로 상대 경로를 절대 경로로 변환"""
    return PROJECT_ROOT / relative_path
