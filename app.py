import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# ---------------------------------------------------------
# 1. 페이지 설정 및 디자인
# ---------------------------------------------------------
st.set_page_config(
    page_title="세종파츠 현장 리포트 Pro",
    page_icon="🚛",
    layout="wide"
)

# 스타일 커스텀 (버튼 크기 키우기 등)
st.markdown("""
<style>
    div.stButton > button {
        width: 100%;
        height: 3em;
        font-weight: bold;
        font-size: 20px;
    }
    .big-font {
        font-size:20px !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("🚛 세종파츠플러스 현장 리포트 Pro")

# ---------------------------------------------------------
# 2. 데이터 로드 및 연결
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 워크시트 데이터 가져오기 (캐시 끄기)
        df = conn.read(worksheet="Sheet1", ttl=0)
        # 날짜순 정렬
        if not df.empty and "날짜" in df.columns:
            df = df.sort_values(by="날짜", ascending=False)
        return df
    except Exception as e:
        return pd.DataFrame()

# ---------------------------------------------------------
# 3. 탭 구성
# ---------------------------------------------------------
tab1, tab2 = st.tabs(["📝 간편 보고 (입력)", "📊 통합 대시보드 (관리)"])

# =========================================================
# [탭 1] 입력 화면 (운전자 최적화 UX)
# =========================================================
with tab1:
    st.info("💡 마이크 버튼을 눌러 말하고, 분류만 톡톡 선택하세요!")

    with st.form(key="report_form", clear_on_submit=True):
        # 1행: 날짜 / 지점
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("📅 날짜", datetime.now())
        with col2:
            branch = st.selectbox("🏢 소속 센터", ["1센터", "2센터", "3센터", "4센터", "기타"])
        
        # 2행: 업무 분류 / 진행 상태 (이게 있어야 엑셀이 편해짐)
        col3, col4 = st.columns(2)
        with col3:
            category = st.selectbox("📂 업무 분류", ["일반방문", "납품/배송", "A/S처리", "클레임/이슈", "기타"])
        with col4:
            status = st.radio("🚦 진행 상태", ["완료", "진행중", "이슈발생"], horizontal=True)

        # 3행: 내용 입력 (음성 입력 타겟)
        st.markdown("**📢 상세 내용 (음성 입력)**")
        content = st.text_area(
            "내용", 
            placeholder="마이크를 켜고 말씀하세요. 예) 수원 거래처 미팅 완료, 재고 부족 요청 받음.",
            height=130,
            label_visibility="collapsed"
        )
        
        # 4행: 제출 버튼
        submit_button = st.form_submit_button(label="🚀 보고서 저장하기")

    # 저장 로직
    if submit_button:
        if not content:
            st.warning("⚠️ 내용을 말씀해주세요!")
        else:
            new_data = pd.DataFrame([{
                "날짜": date.strftime("%Y-%m-%d"),
                "소속": branch,
                "분류": category,  # 엑셀 필터용 핵심
                "상태": status,    # 관리용 핵심
                "내용": content,
                "등록일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])
            
            try:
                existing_data = load_data()
                updated_data = pd.concat([existing_data, new_data], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_data)
                
                st.success("✅ 저장 완료! 대시보드에 반영됩니다.")
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"저장 오류: {e}")

# =========================================================
# [탭 2] 대시보드 (관리자 최적화 UX)
# =========================================================
with tab2:
    st.header("📋 통합 현황판")
    
    df = load_data()
    
    if not df.empty:
        # [기능 1] 검색 및 필터
        col_search, col_download = st.columns([3, 1])
        with col_search:
            search_keyword = st.text_input("🔍 검색 (거래처명, 내용 등)", placeholder="찾고 싶은 키워드를 입력하세요")
        
        # 검색 필터링 로직
        if search_keyword:
            mask = df.apply(lambda x: x.astype(str).str.contains(search_keyword, case=False).any(), axis=1)
            view_df = df[mask]
        else:
            view_df = df

        # [기능 2] 엑셀 다운로드 버튼 (이게 있어야 진짜 편함)
        with col_download:
            csv = view_df.to_csv(index=False).encode('utf-8-sig') # 한글 깨짐 방지
            st.download_button(
                label="💾 엑셀 다운",
                data=csv,
                file_name=f"현장리포트_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

        # [기능 3] 삭제 기능 (체크박스)
        with st.expander("🗑️ 데이터 삭제 모드 열기"):
            st.warning("선택한 항목을 영구 삭제합니다.")
            
            # 식별자 만들기
            df["_id"] = df["날짜"].astype(str) + " " + df["소속"] + " " + df["내용"].str[:5]
            delete_items = st.multiselect("삭제할 항목 선택", df["_id"].unique())
            
            if st.button("선택 항목 삭제 확인"):
                if delete_items:
                    # 삭제 후 남은 데이터
                    clean_df = df[~df["_id"].isin(delete_items)].drop(columns=["_id"])
                    conn.update(worksheet="Sheet1", data=clean_df)
                    st.success("삭제되었습니다.")
                    time.sleep(1)
                    st.rerun()

        # [기능 4] 시각적 확인 (색상 강조)
        st.markdown("---")
        st.write(f"총 **{len(view_df)}**건의 리포트가 있습니다.")
        
        # 데이터프레임 보여주기 (컬럼 순서 정리)
        final_view = view_df[["날짜", "소속", "분류", "상태", "내용", "등록일시"]]
        st.dataframe(
            final_view, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "상태": st.column_config.TextColumn(
                    "상태",
                    help="업무 진행 상태",
                    validate="^(완료|진행중|이슈발생)$"
                )
            }
        )
    else:
        st.info("데이터가 없습니다. 첫 보고를 등록해보세요!")
