"""
수동 평가 컴포넌트
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from pathlib import Path
import sys

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.scoring import calculate_artist_score
from utils.logging_config import get_project_logger
from config import DEFAULT_SCORING_WEIGHTS
from dashboard.components.data_collector import collect_artist_data_realtime
from dashboard.components.charts import create_category_scores_chart, create_correlation_chart

logger = get_project_logger(__name__)


def render_artist_selection(bigc_df: pd.DataFrame):
    """아티스트 선택 인터페이스 렌더링"""
    st.subheader("🎯 아티스트 선택")
    
    selection_method = st.radio(
        "아티스트 선택 방법",
        ["기존 아티스트에서 선택", "새 아티스트 검색"],
        horizontal=True
    )
    
    selected_artist = None
    artist_info = {}
    
    if selection_method == "기존 아티스트에서 선택":
        selected_artist, artist_info = _handle_existing_artist_selection(bigc_df)
    else:
        selected_artist, artist_info = _handle_new_artist_search()
    
    return selected_artist, artist_info


def _handle_existing_artist_selection(bigc_df: pd.DataFrame):
    """기존 아티스트 선택 처리"""
    if bigc_df is None or bigc_df.empty:
        st.warning("BigC 아티스트 데이터를 불러올 수 없습니다.")
        return None, {}
    
    artists_list = sorted(bigc_df['artist'].dropna().unique())
    selected_artist = st.selectbox("아티스트 선택", ["선택하세요..."] + artists_list)
    
    if selected_artist != "선택하세요...":
        artist_row = bigc_df[bigc_df['artist'] == selected_artist].iloc[0]
        artist_info = {
            'name': selected_artist,
            'entertainment': artist_row.get('entertainment', 'N/A'),
            'auto_score': calculate_artist_score(artist_row),
            'instagram': artist_row.get('instagram_followers', 0),
            'twitter': artist_row.get('twitter_followers', 0),
            'spotify': artist_row.get('spotify_followers', 0),
            'popularity': artist_row.get('popularity', 0)
        }
        return selected_artist, artist_info
    
    return None, {}


def _handle_new_artist_search():
    """새 아티스트 검색 처리"""
    new_artist_name = st.text_input("아티스트 이름을 입력하세요")
    
    if new_artist_name:
        if st.button("🔍 실시간 데이터 수집", type="primary"):
            st.write("데이터 수집을 시작합니다...")
            artist_info = collect_artist_data_realtime(new_artist_name)
            st.session_state.collected_data = artist_info
            return new_artist_name, artist_info
        
        # 세션에서 수집된 데이터 사용
        elif 'collected_data' in st.session_state and st.session_state.collected_data['name'] == new_artist_name:
            return new_artist_name, st.session_state.collected_data
    
    return None, {}


def render_artist_info(artist_info: dict):
    """아티스트 정보 표시"""
    st.markdown("---")
    st.subheader(f"📊 {artist_info['name']} 정보")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("소속사", artist_info['entertainment'])
    with col2:
        st.metric("자동 스코어", f"{artist_info['auto_score']:.1f}")
    with col3:
        st.metric("Spotify 팔로워", f"{artist_info['spotify']:,}")
    with col4:
        st.metric("Spotify 인기도", f"{artist_info['popularity']:.1f}")
    
    _render_sns_links(artist_info)


def _render_sns_links(artist_info: dict):
    """SNS 링크 표시"""
    links_exist = any([
        artist_info.get('instagram_link'),
        artist_info.get('youtube_link'),
        artist_info.get('twitter_link'),
        artist_info.get('spotify_url')
    ])
    
    if links_exist:
        st.subheader("🔗 SNS 링크")
        link_cols = st.columns(4)
        
        link_configs = [
            ('instagram_link', '📸 Instagram', 0),
            ('youtube_link', '🎵 YouTube', 1),
            ('twitter_link', '🐦 Twitter', 2),
            ('spotify_url', '🎵 Spotify', 3)
        ]
        
        for link_key, display_name, col_idx in link_configs:
            with link_cols[col_idx]:
                if artist_info.get(link_key):
                    st.markdown(f"[{display_name}]({artist_info[link_key]})")
                else:
                    st.write(f"{display_name}: 없음")


def render_scoring_interface():
    """점수 매기기 인터페이스"""
    st.markdown("---")
    st.subheader("⭐ 점수 매기기")
    
    # 평가 카테고리 설정
    categories = {
        "음악성": {"weight": 25, "description": "작곡, 작사, 보컬, 랩 실력 등"},
        "퍼포먼스": {"weight": 25, "description": "무대 매너, 댄스, 라이브 실력 등"},
        "비주얼": {"weight": 20, "description": "외모, 스타일링, 카리스마 등"},
        "인기도": {"weight": 15, "description": "팬층, 화제성, 미디어 노출 등"},
        "성장 가능성": {"weight": 15, "description": "향후 발전 가능성, 트렌드 적응력 등"}
    }
    
    # 가중치 조정
    categories = _render_weight_adjustment(categories)
    
    # 점수 입력
    scores = _render_score_input(categories)
    
    return categories, scores


def _render_weight_adjustment(categories: dict) -> dict:
    """가중치 조정 인터페이스"""
    with st.expander("🔧 가중치 조정 (기본값 사용 권장)"):
        st.write("각 카테고리의 중요도를 조정할 수 있습니다.")
        for category in categories:
            categories[category]["weight"] = st.slider(
                f"{category} 가중치 (%)",
                min_value=0,
                max_value=50,
                value=categories[category]["weight"],
                step=5
            )
    return categories


def _render_score_input(categories: dict) -> dict:
    """점수 입력 인터페이스"""
    scores = {}
    st.write("**각 항목을 1-10점으로 평가해주세요:**")
    
    for category, info in categories.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            scores[category] = st.slider(
                f"{category} ({info['description']})",
                min_value=1,
                max_value=10,
                value=5,
                step=1,
                key=f"score_{category}"
            )
        with col2:
            st.write(f"가중치: {info['weight']}%")
    
    return scores


def calculate_final_score(categories: dict, scores: dict) -> float:
    """최종 점수 계산"""
    total_weight = sum(cat["weight"] for cat in categories.values())
    if total_weight > 0:
        weighted_score = sum(scores[cat] * categories[cat]["weight"] for cat in scores)
        return (weighted_score / total_weight / 10) * 100  # 100점 만점으로 변환
    return 0


def render_scoring_results(categories: dict, scores: dict, artist_info: dict):
    """평가 결과 표시"""
    final_score = calculate_final_score(categories, scores)
    
    st.markdown("---")
    st.subheader("🏆 평가 결과")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("종합 점수", f"{final_score:.1f}/100")
    with col2:
        st.metric("자동 스코어", f"{artist_info['auto_score']:.1f}/100")
    with col3:
        score_diff = final_score - artist_info['auto_score']
        st.metric("차이", f"{score_diff:+.1f}", delta=f"{score_diff:+.1f}")
    
    # 카테고리별 점수 시각화
    category_df = pd.DataFrame([
        {"카테고리": cat, "점수": scores[cat], "가중치": info["weight"]}
        for cat, info in categories.items()
    ])
    
    fig = create_category_scores_chart(category_df)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    
    return final_score


def save_manual_score(artist_info: dict, final_score: float, categories: dict, scores: dict):
    """수동 점수 저장"""
    if st.button("💾 점수 저장", type="primary"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        score_data = {
            'timestamp': timestamp,
            'artist': artist_info['name'],
            'entertainment': artist_info['entertainment'],
            'manual_score': final_score,
            'auto_score': artist_info['auto_score'],
            'categories': scores,
            'weights': {cat: info["weight"] for cat, info in categories.items()}
        }
        
        # 세션 상태에 저장
        if 'manual_scores' not in st.session_state:
            st.session_state.manual_scores = {}
        
        st.session_state.manual_scores[f"{artist_info['name']}_{timestamp}"] = score_data
        st.success(f"✅ {artist_info['name']}의 점수가 저장되었습니다!")
        st.balloons()


def render_score_history():
    """저장된 점수 히스토리 표시"""
    if 'manual_scores' not in st.session_state or not st.session_state.manual_scores:
        return
    
    st.markdown("---")
    st.subheader("📈 평가 히스토리")
    
    # 히스토리 데이터 변환
    history_data = []
    for key, data in st.session_state.manual_scores.items():
        history_data.append({
            '평가일시': data['timestamp'],
            '아티스트': data['artist'],
            '소속사': data['entertainment'],
            '수동점수': f"{data['manual_score']:.1f}",
            '자동점수': f"{data['auto_score']:.1f}",
            '차이': f"{data['manual_score'] - data['auto_score']:+.1f}"
        })
    
    history_df = pd.DataFrame(history_data)
    history_df = history_df.sort_values('평가일시', ascending=False)
    
    st.dataframe(history_df, use_container_width=True)
    
    # 히스토리 차트
    if len(history_data) > 1:
        fig = create_correlation_chart(history_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    
    # 히스토리 초기화 버튼
    if st.button("🗑️ 히스토리 초기화"):
        st.session_state.manual_scores = {}
        st.rerun()