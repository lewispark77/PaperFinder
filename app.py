import streamlit as st
import requests
from deep_translator import GoogleTranslator
import pandas as pd

# 1. OpenAlex API 호출 함수
@st.cache_data(show_spinner=False, ttl=3600)
def search_openalex(query, limit=10):
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per-page": limit,
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
# 4. 웹 UI 구성
# ==========================================
st.set_page_config(page_title="Mini SciFinder", page_icon="🔬", layout="centered")

st.title("🔬 나만의 미니 논문 검색 포털")
st.write("키워드를 검색하고 결과를 **엑셀(CSV) 파일로 다운로드** 하세요.")

# 검색 폼 디자인 구성
with st.form("search_box"):
    query = st.text_input("검색어 (영어 권장)", placeholder="예: Molded Underfill, EMC packaging...")
    
    # 옵션들을 나란히 배치하기 위해 컬럼 분할
    col1, col2 = st.columns(2)
    with col1:
        limit = st.selectbox("검색 결과 수", [10, 20, 30], index=0)
    with col2:
        # 번역 켜기/끄기 체크박스 추가 (기본값: 켜짐)
        st.write("") # 높이 맞춤용 빈 줄
        enable_translation = st.checkbox("🇰🇷 한국어로 자동 번역하기", value=True)
        
    submit = st.form_submit_button("논문 검색 시작")

# 검색 실행 로직
if submit:
    if query:
        # 번역 여부에 따라 로딩 메시지 다르게 표시
        loading_msg = "🚀 검색 및 한글 번역 중입니다..." if enable_translation else "⚡ 영문 원본을 빠르게 검색 중입니다..."
        
        with st.spinner(loading_msg):
            papers = search_openalex(query, limit)

            if papers:
                st.success(f"'{query}' 관련 논문 {len(papers)}개를 찾았습니다.")
                results_for_excel = []
                
                for i, paper in enumerate(papers, 1):
                    # 기본 정보 추출
                    original_title = paper.get("title", "제목 없음")
                    year = paper.get("publication_year", "연도 미상")
                    
                    primary_loc = paper.get("primary_location") or {}
                    url = primary_loc.get("landing_page_url") or paper.get("doi") or "#"
                    
                    authorships = paper.get("authorships", [])
                    authors_list = [a.get("author", {}).get("display_name", "") for a in authorships]
                    authors = ", ".join(authors_list) if authors_list else "저자 정보 없음"
                    
                    abstract_idx = paper.get("abstract_inverted_index", {})
                    original_abstract = build_abstract(abstract_idx)

                    # --- 체크박스 상태에 따른 번역 로직 ---
                    if enable_translation:
                        display_title = translate_text(original_title)
                        ko_abstract = translate_text(original_abstract) if original_abstract else "초록 없음"
                    else:
                        display_title = original_title
                        ko_abstract = "" # 번역 껐을 땐 사용 안 함

                    # 화면에 결과 출력
                    with st.container():
                        st.markdown(f"### {i}. [{display_title}]({url})")
                        
                        if enable_translation:
                            st.caption(f"원제: {original_title}") 
                            
                        st.write(f"- **출판 연도:** {year}")
                        st.write(f"- **저자:** {authors}")
                        
                        with st.expander("📄 초록(Abstract) 보기"):
                            if original_abstract:
                                if enable_translation:
                                    st.markdown("**[한글 번역]**")
                                    st.write(ko_abstract)
                                    st.divider()
                                    st.markdown("**[English Abstract]**")
                                    st.write(original_abstract)
                                else:
                                    # 번역을 껐을 땐 영문 원본만 깔끔하게 표시
                                    st.write(original_abstract)
                            else:
                                st.write("제공된 초록이 없습니다.")
                        st.divider()

                    # --- 체크박스 상태에 따른 엑셀 데이터 저장 로직 ---
                    row_data = {
                        "제목": display_title,
                        "저자": authors,
                        "출판 연도": year,
                        "원문 링크": url,
                    }
                    
                    if enable_translation:
                        row_data["원래 제목(영문)"] = original_title
                        row_data["한글 초록"] = ko_abstract
                        row_data["원문 초록(영문)"] = original_abstract
                    else:
                        row_data["초록(영문)"] = original_abstract

                    results_for_excel.append(row_data)

                # 엑셀 다운로드 버튼 생성
                df = pd.DataFrame(results_for_excel)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                
                st.download_button(
                    label="📥 검색 결과 엑셀(CSV)로 다운로드",
                    data=csv,
                    file_name=f"{query}_논문검색결과.csv",
                    mime="text/csv"
                )

            else:
                st.warning("검색 결과가 없습니다. 다른 키워드로 시도해 보세요.")
    else:
        st.warning("검색어를 입력해 주세요.")