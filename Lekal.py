import streamlit as st
import pandas as pd
import os
import zipfile
import io
from datetime import datetime, date, time

# === [系統核心設定] ===
# 使用 lan_ 前綴區隔資料
DB_FILE = "lan_lessons.csv"
REQ_FILE = "lan_requests.csv"
STU_FILE = "lan_students.csv"
CAT_FILE = "lan_categories.csv"
EVT_FILE = "lan_events.csv"
COACH_PASSWORD = "888"

st.set_page_config(page_title="嵐教練健身管理系統", layout="wide", page_icon="⚡")

# --- 核心防崩潰檢查：嘗試載入日曆 ---
try:
    from streamlit_calendar import calendar
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

# === [資料庫初始化邏輯] ===
SCHEMA = {
    DB_FILE: ["日期", "時間", "學員", "課程種類", "備註"],
    REQ_FILE: ["日期", "時間", "姓名", "留言"],
    STU_FILE: ["姓名", "購買堂數", "課程類別", "備註"],
    CAT_FILE: ["類別名稱"],
    EVT_FILE: ["日期", "時間", "事項", "類型"]
}

def init_system():
    for f, cols in SCHEMA.items():
        if not os.path.exists(f):
            if f == CAT_FILE:
                pd.DataFrame({"類別名稱": ["私人教練課", "團體體態課", "專項訓練"]}).to_csv(f, index=False)
            else:
                pd.DataFrame(columns=cols).to_csv(f, index=False)

init_system()

@st.cache_data(ttl=5)
def load_data():
    # 讀取並轉換日期格式
    d_db = pd.read_csv(DB_FILE)
    d_db["日期"] = pd.to_datetime(d_db["日期"], errors='coerce').dt.date
    d_stu = pd.read_csv(STU_FILE)
    d_req = pd.read_csv(REQ_FILE)
    d_cat = pd.read_csv(CAT_FILE)
    d_evt = pd.read_csv(EVT_FILE)
    d_evt["日期"] = pd.to_datetime(d_evt["日期"], errors='coerce').dt.date
    return d_db, d_stu, d_req, d_cat, d_evt

df_db, df_stu, df_req, df_cat, df_evt = load_data()
ALL_CATS = sorted(df_cat["類別名稱"].unique().tolist())
STU_LIST = sorted(df_stu["姓名"].unique().tolist())

# === [介面美化 CSS] ===
st.markdown("""
    <style>
    .stApp { background-color: #f9f9f9; }
    .main-header { font-size: 2.5rem; color: #1E88E5; font-weight: 800; }
    .info-card { padding: 1.5rem; border-radius: 10px; background: white; border-left: 5px solid #1E88E5; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">⚡ 嵐教練專屬課程管理</div>', unsafe_allow_html=True)

# === [視覺化日曆區塊] ===
with st.container():
    if HAS_CALENDAR:
        events = []
        # 課程事件
        for _, row in df_db.iterrows():
            if pd.isna(row['日期']): continue
            events.append({
                "title": f"👤 {row['學員']}",
                "start": f"{row['日期']}T{row['時間']}:00",
                "end": f"{row['日期']}T{int(row['時間'].split(':')[0])+1:02d}:00:00",
                "color": "#1E88E5"
            })
        # 行事曆事件
        for _, row in df_evt.iterrows():
            if pd.isna(row['日期']): continue
            events.append({
                "title": f"🚩 {row['事項']}",
                "start": f"{row['日期']}",
                "allDay": True if row['時間'] == "全天" else False,
                "color": "#FFA000"
            })
        
        calendar(events=events, options={"locale": "zh-tw", "height": 500}, key="main_cal")
    else:
        st.warning("⚠️ 系統偵測到未安裝 `streamlit-calendar`。請在終端機執行 `pip install streamlit-calendar`。")
        st.info("💡 目前將以「今日課表清單」代替圖形日曆。")
        today_df = df_db[df_db["日期"] == date.today()]
        st.table(today_df if not today_df.empty else pd.DataFrame(columns=["今日無課"]))

st.divider()

# === [分頁導覽] ===
tab_s, tab_c = st.tabs(["🔍 學員專區", "🔒 教練後台"])

with tab_s:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("💳 餘額查詢")
        if STU_LIST:
            s_name = st.selectbox("請選擇姓名", STU_LIST)
            stu_info = df_stu[df_stu["姓名"] == s_name].iloc[0]
            used = len(df_db[df_db["學員"] == s_name])
            total = int(stu_info["購買堂數"])
            rem = total - used
            st.markdown(f"""<div class="info-card"><h4>{s_name} 同學</h4><h5>剩餘：{rem} 堂 / 總計：{total} 堂</h5></div>""", unsafe_allow_html=True)
            if rem <= 2: st.error("🚨 堂數即將用完，請聯繫嵐教練！")
        else: st.info("尚無學員名單")

    with col2:
        st.subheader("📝 預約留言")
        with st.form("req_form"):
            r_d = st.date_input("預約日期")
            r_t = st.selectbox("預約時段", [f"{h:02d}:00" for h in range(7, 23)])
            r_n = st.text_input("姓名")
            r_m = st.text_area("留言")
            if st.form_submit_button("送出"):
                new_r = pd.DataFrame([{"日期":str(r_d), "時間":r_t, "姓名":r_n, "留言":r_m}])
                pd.concat([df_req, new_r]).to_csv(REQ_FILE, index=False)
                st.success("已送出！")

with tab_c:
    pwd = st.text_input("後台密碼", type="password")
    if pwd == COACH_PASSWORD:
        m1, m2, m3, m4 = st.tabs(["➕ 快速排課", "👥 學員名單", "💬 留言管理", "💾 系統備份"])
        
        with m1:
            with st.form("add_l"):
                c1, c2, c3 = st.columns(3)
                ld = c1.date_input("日期", date.today())
                lt = c2.selectbox("時間", [f"{h:02d}:00" for h in range(7, 23)])
                ls = c3.selectbox("學員", ["(請選擇)"] + STU_LIST)
                lcat = st.selectbox("項目", ALL_CATS)
                note = st.text_input("備註")
                if st.form_submit_button("確認排課"):
                    if ls != "(請選擇)":
                        new_l = pd.DataFrame([{"日期":ld, "時間":lt, "學員":ls, "課程種類":lcat, "備註":note}])
                        pd.concat([df_db, new_l]).to_csv(DB_FILE, index=False)
                        st.success("成功！"); st.rerun()
            st.dataframe(df_db.tail(10), use_container_width=True)

        with m2:
            st.subheader("學員檔案維護")
            e_stu = st.data_editor(df_stu, num_rows="dynamic", use_container_width=True)
            if st.button("儲存名單"):
                e_stu.to_csv(STU_FILE, index=False); st.rerun()

        with m3:
            st.subheader("學員預約訊息")
            st.dataframe(df_req, use_container_width=True)
            if st.button("清空留言"):
                pd.DataFrame(columns=SCHEMA[REQ_FILE]).to_csv(REQ_FILE, index=False); st.rerun()

        with m4:
            st.subheader("數據導出")
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "x") as zf:
                for f in SCHEMA.keys():
                    if os.path.exists(f): zf.write(f)
            st.download_button("⬇️ 下載備份 ZIP", buf.getvalue(), f"backup_{date.today()}.zip")

st.caption(f"© 2026 嵐教練健身系統 | 伺服器時間: {datetime.now().strftime('%H:%M')}")
