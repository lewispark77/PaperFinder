import streamlit as st
import requests
from deep_translator import GoogleTranslator
import pandas as pd
import time

# ==========================================
# 1. OpenAlex API 호출 함수
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

# 2. OpenAlex 초록 조립 함수
def build_abstract(inverted_index):
    if not inverted_index: return ""
    try:
        max_idx = max([max(positions) for positions in inverted_index.values()])
        words = [""] * (max_idx + 1)
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        return " ".join(words).strip()
    except:
        return ""

# 3. 한글 번역 함수
@st.cache_data(show_spinner=False)
def translate_text(text):
    if not text or text.strip() == "": return ""
    try:
        return GoogleTranslator(source='en', target='ko').translate(text)
    except: return text 

# ==========================================
# 4. 세션 상태 초기화
# ==========================================
if "all_papers" not in st.session_state:
    st.session_state.all_papers = []
if "current_page" not in st.session_state:
    st.session_state.current_page = 1
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

# ==========================================
# 5. 웹 UI 구성
# ==========================================
st.set_page_config(page_title="PaperFinder", page_icon="🔬", layout="centered")

st.title("🔬 PaperFinder: 무료 논문 검색")
st.markdown("전 세계 학술 논문을 검색하고, 결과를 **엑셀(CSV)로 누적 다운로드** 하세요.")

with st.form("search_box"):
    query = st.text_input("검색어 (영어 권장)", placeholder="예: HBM semiconductor, MUF packaging...", value=st.session_state.last_query)
    
    col1, col2 = st.columns(2)
    with col1:
        limit = st.selectbox("한 번에 불러올 결과 수", [10, 20, 30], index=2)
    with col2:
        st.write("") 
        enable_translation = st.checkbox("🇰🇷 한국어로 자동 번역하기", value=False) # 디폴트 영어(False)로 설정
        
    submit = st.form_submit_button("신규 논문 검색 시작")

# ==========================================
# 6. 신규 검색 로직 (상태 표시기 적용)
# ==========================================
if submit:
    if query:
        st.session_state.all_papers = []
        st.session_state.current_page = 1
        st.session_state.last_query = query
        
        # 시각적 효과: 드롭다운 형태의 진행 상태 표시창
        with st.status("🔍 글로벌 데이터베이스에서 핵심 논문을 스캔 중입니다...", expanded=True) as status:
            st.write("📡 API 서버와 통신 중...")
            new_papers = search_openalex(query, limit, page=1)
            
            if new_papers:
                st.write(f"✅ {len(new_papers)}개의 논문 데이터를 성공적으로 확보했습니다.")
                st.session_state.all_papers = new_papers
                status.update(label="✨ 검색 및 데이터 확보 완료!", state="complete", expanded=False)
            else:
                status.update(label="❌ 검색 결과가 없습니다.", state="error", expanded=False)
    else:
        st.warning("검색어를 입력해 주세요.")

# ==========================================
# 7. 결과 출력 및 프로그레스 바 (로딩 바)
# ==========================================
if st.session_state.all_papers:
    st.success(f"현재까지 총 {len(st.session_state.all_papers)}개의 논문을 확보했습니다. (페이지: {st.session_state.current_page})")
    
    # 로딩 바 설정
    if enable_translation:
        progress_text = "🔄 AI가 영문 논문을 한국어로 번역 및 정리하고 있습니다..."
    else:
        progress_text = "🔄 논문 데이터를 화면에 정리하고 있습니다..."
        
    my_bar = st.progress(0, text=progress_text)
    
    results_for_excel = []
    total_papers = len(st.session_state.all_papers)
    
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
            st.markdown(f"### {i}. [{display_title}]({url})")
            if enable_translation: st.caption(f"원제: {original_title}") 
            st.write(f"- **출판 연도:** {year} | **저자:** {authors}")
            with st.expander("📄 초록(Abstract) 보기"):
                if original_abstract:
                    if enable_translation:
                        st.markdown("**[한글 번역]**")
                        st.write(ko_abstract)
                        st.divider()
                    st.write(original_abstract)
                else:
                    st.write("제공된 초록이 없습니다.")
            st.divider()

        # 데이터 저장 (엑셀용)
        row_data = {"제목": display_title, "저자": authors, "출판 연도": year, "원문 링크": url}
        if enable_translation:
            row_data.update({"영문 제목": original_title, "한글 초록": ko_abstract, "영문 초록": original_abstract})
        else:
            row_data["초록"] = original_abstract
        results_for_excel.append(row_data)
        
        # 로딩 바 게이지 채우기
        percent_complete = int((i / total_papers) * 100)
        my_bar.progress(percent_complete, text=f"{progress_text} ({i}/{total_papers})")

    # 출력이 끝나면 로딩 바 숨기기
    my_bar.empty()

    # 8. 하단 버튼 구역 (페이지네이션 상태 표시기 추가)
    col_more, col_down = st.columns(2)
    
    with col_more:
        if st.button("➕ 다음 결과 더 가져오기"):
            st.session_state.current_page += 1
            
            with st.status(f"🔍 {st.session_state.current_page}페이지 데이터를 스캔 중입니다...", expanded=True) as status:
                st.write("📡 통신 중...")
                more_papers = search_openalex(st.session_state.last_query, limit, page=st.session_state.current_page)
                if more_papers:
                    st.session_state.all_papers.extend(more_papers)
                    status.update(label="✨ 추가 데이터 확보 완료!", state="complete", expanded=False)
                    st.rerun() # 화면 갱신
                else:
                    status.update(label="더 이상의 검색 결과가 없습니다.", state="error", expanded=False)
                    st.info("마지막 페이지입니다.")

    with col_down:
        df = pd.DataFrame(results_for_excel)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 누적 데이터 엑셀 다운로드",
            data=csv,
            file_name=f"PaperFinder_{st.session_state.last_query}_누적결과.csv",
            mime="text/csv"
        )
