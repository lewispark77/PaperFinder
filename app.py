import streamlit as st
import requests
from deep_translator import GoogleTranslator
import pandas as pd
import time

# ==========================================
# 1. 페이지 기본 설정 (와이드 모드 적용)
# ==========================================
st.set_page_config(
    page_title="PaperFinder", 
    page_icon="🔬", 
    layout="wide", # 화면을 양옆으로 꽉 채웁니다.
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. 커스텀 디자인 (CSS) - 연구소 플랫폼 느낌
# ==========================================
st.markdown("""
    <style>
    /* 메인 배경색 */
    .stApp {
        background-color: #fcfcfc;
    }
    /* 버튼 디자인: 메인 컬러 파란색으로 변경 */
    div.stButton > button:first-child {
        background-color: #004a99;
        color: white;
        border-radius: 8px;
        height: 3em;
        width: 100%;
        font-weight: bold;
        border: none;
    }
    /* 버튼에 마우스 올렸을 때 효과 */
    div.stButton > button:first-child:hover {
        background-color: #003366;
        color: #ffca28;
    }
    /* 타이틀 및 헤더 색상 */
    h1 { color: #003366 !important; }
    h3 { color: #1a1a1a !important; }
    
    /* 사이드바 꾸미기 */
    .css-1d391kg {
        background-color: #f0f2f6;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 데이터 처리 함수들
# ==========================================
@st.cache_data(show_spinner=False, ttl=3600)
def search_openalex(query, limit=30, page=1):
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per-page": limit,
        "page": page,
        "mailto": "ari4567@gmail.com" 
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except Exception as e:
        st.error(f"OpenAlex 통신 오류: {e}")
        return []

def build_abstract(inverted_index):
    if not inverted_index: return ""
    try:
        max_idx = max([max(positions) for positions in inverted_index.values()])
        words = [""] * (max_idx + 1)
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        return " ".join(words).strip()
    except: return ""

@st.cache_data(show_spinner=False)
def translate_text(text):
    if not text or text.strip() == "": return ""
    try:
        return GoogleTranslator(source='en', target='ko').translate(text)
    except: return text 

# ==========================================
# 4. 세션 상태 및 사이드바
# ==========================================
if "all_papers" not in st.session_state:
    st.session_state.all_papers = []
if "current_page" not in st.session_state:
    st.session_state.current_page = 1
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

# 사이드바에 정보 넣기 (연구소 플랫폼 느낌)
with st.sidebar:
    st.header("🔬 PaperFinder 정보")
    st.info("전 세계 연구 데이터를 실시간 스캔하여 연구 효율을 극대화합니다.")
    st.markdown("---")
    st.write("💡 **팁:** 검색 후 '엑셀 다운로드'를 누르면 나중에 논문을 하나하나 찾을 필요 없이 한눈에 관리할 수 있습니다.")
    st.write("📢 **문의:** ari4567@gmail.com")

# ==========================================
# 5. 메인 UI
# ==========================================
st.title("🔬 PaperFinder: 무료 논문 검색")
st.write("연구원을 위한 최적화된 논문 매집 도구입니다.")

with st.form("search_box"):
    query = st.text_input("검색어 (영어 권장)", placeholder="예: HBM, MUF, Palantir AI...", value=st.session_state.last_query)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        limit = st.selectbox("한 번에 불러올 결과 수", [10, 20, 30, 50], index=2)
    with col2:
        st.write("") 
        st.write("") # 간격 맞추기용
        enable_translation = st.checkbox("🇰🇷 한국어로 자동 번역하기", value=False)
        
    submit = st.form_submit_button("🚀 신규 논문 검색 및 데이터 스캔 시작")

# ==========================================
# 6. 검색 실행 및 결과 출력
# ==========================================
if submit:
    if query:
        st.session_state.all_papers = []
        st.session_state.current_page = 1
        st.session_state.last_query = query
        
        with st.status("🔍 글로벌 데이터베이스에서 핵심 논문을 스캔 중입니다...", expanded=True) as status:
            st.write("📡 데이터 서버 연결 중...")
            new_papers = search_openalex(query, limit, page=1)
            
            if new_papers:
                st.write(f"✅ {len(new_papers)}개의 고급 연구 데이터 확보 성공!")
                st.session_state.all_papers = new_papers
                status.update(label="✨ 검색 완료!", state="complete", expanded=False)
            else:
                status.update(label="❌ 결과를 찾을 수 없습니다.", state="error", expanded=False)
    else:
        st.warning("검색어를 입력해 주세요.")

if st.session_state.all_papers:
    st.divider()
    
    # 엑셀용 데이터 정리 및 로딩 바
    progress_text = "🔄 연구 데이터를 정리하고 있습니다..."
    my_bar = st.progress(0, text=progress_text)
    
    results_for_excel = []
    total_papers = len(st.session_state.all_papers)
    
    # 결과 출력
    cols = st.columns(1) # 와이드 모드이므로 1열로 넓게 출력
    for i, paper in enumerate(st.session_state.all_papers, 1):
        original_title = paper.get("title", "제목 없음")
        year = paper.get("publication_year", "연도 미상")
        primary_loc = paper.get("primary_location") or {}
        url = primary_loc.get("landing_page_url") or paper.get("doi") or "#"
        authorships = paper.get("authorships", [])
        authors_list = [a.get("author", {}).get("display_name", "") for a in authorships]
        authors = ", ".join(authors_list) if authors_list else "저자 정보 없음"
        abstract_idx = paper.get("abstract_inverted_index", {})
        original_abstract = build_abstract(abstract_idx)

        if enable_translation:
            display_title = translate_text(original_title)
            ko_abstract = translate_text(original_abstract) if original_abstract else "초록 없음"
        else:
            display_title = original_title
            ko_abstract = ""

        with st.container():
            st.markdown(f"#### {i}. [{display_title}]({url})")
            if enable_translation: st.caption(f"Original Title: {original_title}")
            st.write(f"📅 **연도:** {year} | 👤 **저자:** {authors}")
            
            with st.expander("📄 논문 초록(Abstract) 상세보기"):
                if original_abstract:
                    if enable_translation:
                        st.markdown("**[한글 번역]**")
                        st.write(ko_abstract)
                        st.divider()
                    st.write(original_abstract)
                else:
                    st.write("제공된 초록이 없습니다.")
            st.divider()

        # 데이터 저장
        row_data = {"번호": i, "제목": display_title, "저자": authors, "연도": year, "링크": url}
        if enable_translation:
            row_data.update({"영문제목": original_title, "한글초록": ko_abstract, "영문초록": original_abstract})
        else:
            row_data["초록"] = original_abstract
        results_for_excel.append(row_data)
        
        # 로딩 바 업데이트
        my_bar.progress(int((i / total_papers) * 100), text=f"{progress_text} ({i}/{total_papers})")

    my_bar.empty()

    # 하단 컨트롤 바
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("➕ 다음 페이지 더 보기"):
            st.session_state.current_page += 1
            st.rerun()
    with c2:
        df = pd.DataFrame(results_for_excel)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 전체 결과 엑셀로 저장",
            data=csv,
            file_name=f"PaperFinder_{st.session_state.last_query}.csv",
            mime="text/csv"
        )
    with c3:
        st.write(f"현재 데이터: **{total_papers}건**")
