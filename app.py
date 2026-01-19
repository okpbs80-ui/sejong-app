import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 기본 설정 및 보안 ---
st.set_page_config(page_title="세종파츠플러스 업무보고", page_icon="🚗")

# 단순 비밀번호 설정 (1234)
PASSWORD = "1234"

def check_password():
    """비밀번호 확인 함수"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        pwd = st.text_input("비밀번호를 입력하세요", type="password")
        if pwd == PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
        elif pwd:
            st.error("비밀번호가 틀렸습니다.")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. 구글 시트 연결 ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    data = conn.read(worksheet="시트1", usecols=list(range(7)), ttl=5)
    df = pd.DataFrame(data)
    if not df.empty and '작성일' in df.columns:
        df = df.sort_values(by='작성일', ascending=False)
except Exception as e:
    st.error(f"구글 시트 연결 오류: {e}")
    st.stop()

# --- 3. 화면 구성 ---
st.title("🚗 세종파츠플러스 현장 리포트")
tab1, tab2 = st.tabs(["📝 업무 보고 작성", "📊 통합 대시보드"])

# === 탭 1: 보고 작성 ===
with tab1:
    st.subheader("일일 업무 및 이슈 보고")
    with st.form("report_form"):
        col1, col2 = st.columns(2)
        with col1:
            center_name = st.selectbox("지점/센터명", ["1센터", "2센터", "3센터", "4센터", "본부장"])
            category = st.selectbox("카테고리", ["현장영업", "팀내이슈", "아이디어","전달사항","개인/보안(비공개)"])
        with col2:
            priority = st.radio("중요도", ["보통", "긴급 🔥"], horizontal=True)
            status = st.radio("진행 상태", ["진행중", "완료"], horizontal=True)
        
        st.info("💡 모바일 키보드의 '마이크' 버튼을 누르면 음성으로 입력할 수 있습니다.")
        content = st.text_area("내용 입력", height=150)
        
        if st.form_submit_button("보고서 제출"):
            if not content:
                st.warning("내용을 입력해주세요.")
            else:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_data = pd.DataFrame([{
                    "작성일": now, "센터명": center_name, "카테고리": category,
                    "중요도": priority, "내용": content, "진행상태": status, "본사피드백": ""
                }])
                updated_df = pd.concat([df, new_data], ignore_index=True)
                conn.update(worksheet="시트1", data=updated_df)
                st.success("제출 완료!")
                st.rerun()

# === 탭 2: 대시보드 ===
with tab2:
    st.subheader("전국 지점 현황판")
    col1, col2, col3 = st.columns(3)
    with col1: view_security = st.checkbox("🔒 보안 내용 표시", value=False)
    with col2: filter_status = st.multiselect("상태 필터", ["진행중", "완료"], default=["진행중"])
    with col3: filter_center = st.multiselect("센터 필터", df['센터명'].unique() if not df.empty else [])

    if not df.empty:
        filtered_df = df.copy()
        if not view_security: filtered_df = filtered_df[filtered_df['카테고리'] != "개인/보안(비공개)"]
        if filter_status: filtered_df = filtered_df[filtered_df['진행상태'].isin(filter_status)]
        if filter_center: filtered_df = filtered_df[filtered_df['센터명'].isin(filter_center)]

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    else:
        st.info("데이터가 없습니다.")
