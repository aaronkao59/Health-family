import streamlit as st
import pandas as pd
import os
import hashlib
import zipfile 
import io      
from datetime import datetime, date, time
import altair as alt

# --- [系統設定] ---
DB_FILE = "lan_lessons.csv"
REQ_FILE = "lan_requests.csv"
STU_FILE = "lan_students.csv"
CAT_FILE = "lan_categories.csv"
COACH_EVT_FILE = "lan_coach_events.csv"
COACH_PASSWORD = "888" 

st.set_page_config(page_title="嵐教練健身管理系統", layout="wide", page_icon="⚡")

# --- [視覺風格定義] ---
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    .main-header { font-size: 2.2rem; font-weight: 800; color: #1E88E5; margin-bottom: 1rem; }
    .card {
        padding: 20px; border-radius: 15px; background: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-top: 5px solid #1E88E5;
        transition: 0.3s ease;
    }
    .card:hover { transform: translateY(-5px); }
    .status-tag { padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

try:
    from streamlit_calendar import calendar
except ImportError:
    st.error("請執行：pip install streamlit-calendar")

# --- [資料核心引擎] ---
SCHEMA = {
    DB_FILE: ["日期", "時間", "學員", "課程種類", "備註"],
    REQ_FILE: ["日期", "時間", "姓名", "留言"],
    STU_FILE: ["姓名", "購買堂數", "課程類別", "備註"],
    CAT_FILE: ["類別名稱"],
    COACH_EVT_FILE: ["日期", "時間", "事項", "類型", "備註"]
}

@st.cache_data(ttl=10) # 縮短快取時間，確保留言即時顯示
def load_all_data():
    results = []
    for f, cols in SCHEMA.items():
        if not os.path.exists(f):
            df = pd.DataFrame(columns=cols)
            if f == CAT_FILE: df = pd.DataFrame({"類別名稱": ["私人教練課", "團體體態課", "專項訓練"]})
            df.to_csv(f, index=False)
        
        tmp_df = pd.read_csv(f)
        if "日期" in tmp_df.columns:
            tmp_df["日期"] = pd.to_datetime(tmp_df["日期"], errors='coerce').dt.date
        results.append(tmp_df)
    return results

df_db, df_req, df_stu, df_cat, df_evt = load_all_data()

# 下拉選單預整理
ALL_CATS = sorted(df_cat["類別名稱"].unique().tolist()) if not df_cat.empty else ["一般課程"]
STU_LIST = sorted(df_stu["姓名"].unique().tolist()) if not df_stu.empty else []

def get_cat_color(cat_name):
    # 為不同課程生成固定顏色
    colors = ["#1E88E5", "#43A047", "#E53935", "#8E24AA", "#FB8C00", "#3949AB"]
    idx = hash(cat_name) % len(colors)
    return colors[idx]

# --- [UI 佈局] ---
st.markdown('<div class="main-header">⚡ 嵐教練專屬課程表</div>', unsafe_allow_html=True)

# 1. 頂部日曆
events = []
# 課程事件
for _, row in df_db.iterrows():
    if pd.isna(row['日期']): continue
    c_color = get_cat_color(row['課程種類'])
    try:
        start_h = int(str(row['時間']).split(':')[0])
        events.append({
            "title": f"👤 {row['學員']}",
            "start": f"{row['日期']}T{start_h:02d}:00:00",
            "end": f"{row['日期']}T{start_h+1:02d}:00:00",
            "backgroundColor": "white",
            "textColor": c_color,
            "borderColor": c_color,
            "extendedProps": {"note": row['備註']}
        })
    except: pass

# 教練行程事件
for _, row in df_evt.iterrows():
    if pd.isna(row['日期']): continue
    is_rest = row['類型'] == "排休"
    events.append({
        "title": f"🚩 {row['事項']}",
        "start": f"{row['日期']}",
        "allDay": True if row['時間'] == "全天" else False,
        "backgroundColor": "#FEEBC8" if is_rest else "#E9D8FD",
        "textColor": "#7B341E" if is_rest else "#44337A",
        "display": "block"
    })

cal_options = {
    "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek,listMonth"},
    "locale": "zh-tw",
    "height": 500,
}
calendar(events=events, options=cal_options, key="lan_v2_cal")

st.divider()

# 2. 功能分區
tab_stu, tab_coach = st.tabs(["🔍 學員自助查詢", "🔒 教練管理中心"])

with tab_stu:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("💳 餘額與預約")
        if STU_LIST:
            sel_stu = st.selectbox("請選擇您的姓名", STU_LIST)
            stu_row = df_stu[df_stu["姓名"] == sel_stu].iloc[0]
            done = len(df_db[df_db["學員"] == sel_stu])
            total = int(stu_row["購買堂數"])
            rem = total - done
            
            # 視覺化卡片
            status_color = "#E53935" if rem <= 2 else "#1E88E5"
            st.markdown(f"""
                <div class="card" style="border-top-color: {status_color}">
                    <h3>{sel_stu} 同學</h3>
                    <p>剩餘堂數：<span style="font-size: 1.5rem; color:{status_color}; font-weight:bold;">{rem}</span> / {total}</p>
                </div>
            """, unsafe_allow_html=True)
            
            if rem <= 2: st.warning("⚠️ 堂數快用完囉，記得找嵐教練續課！")
            
            with st.expander("📝 留話/預約新時段"):
                with st.form("stu_msg"):
                    d_pick = st.date_input("希望日期")
                    t_pick = st.selectbox("希望時段", [f"{h:02d}:00" for h in range(7, 23)])
                    msg = st.text_area("備註內容")
                    if st.form_submit_button("送出訊息"):
                        new_req = pd.DataFrame([{"日期":str(d_pick), "時間":t_pick, "姓名":sel_stu, "留言":msg}])
                        pd.concat([df_req, new_req]).to_csv(REQ_FILE, index=False)
                        st.success("教練已收到您的預約！")
        else:
            st.info("目前名單中還沒有學員資料。")

    with c2:
        st.subheader("📅 今日課表")
        today_data = df_db[df_db["日期"] == date.today()].sort_values("時間")
        if not today_data.empty:
            for _, r in today_data.iterrows():
                st.markdown(f"""
                    <div style="background: white; padding: 10px; border-radius: 8px; border-left: 4px solid {get_cat_color(r['課程種類'])}; margin-bottom: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                        <b>{r['時間']}</b> | {r['學員']} | <small>{r['課程種類']}</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.write("☕ 今天嵐教練目前沒有排課，好好休息！")

with tab_coach:
    pwd = st.text_input("後台驗證密碼", type="password")
    if pwd == COACH_PASSWORD:
        m1, m2, m3, m4 = st.tabs(["➕ 快速排課", "👥 名單維護", "📊 數據中心", "⚙️ 設定"])
        
        with m1:
            with st.form("add_l"):
                col_a, col_b, col_c = st.columns(3)
                d = col_a.date_input("日期", date.today())
                t = col_b.selectbox("時間", [f"{h:02d}:00" for h in range(7, 23)])
                s = col_c.selectbox("學員", STU_LIST)
                
                cat_default = ALL_CATS[0]
                if s:
                    match = df_stu[df_stu["姓名"] == s]
                    if not match.empty: cat_default = match.iloc[0]["課程類別"]
                
                cat = st.selectbox("課程類別", ALL_CATS, index=ALL_CATS.index(cat_default) if cat_default in ALL_CATS else 0)
                note = st.text_input("課程備註")
                if st.form_submit_button("完成排課"):
                    new_l = pd.DataFrame([{"日期":d, "時間":t, "學員":s, "課程種類":cat, "備註":note}])
                    pd.concat([df_db, new_l], ignore_index=True).to_csv(DB_FILE, index=False)
                    st.success("排課成功！")
                    st.rerun()
            
            st.subheader("📋 最近排課紀錄")
            edited_db = st.data_editor(df_db.tail(15), num_rows="dynamic", use_container_width=True)
            if st.button("儲存修改內容"):
                edited_db.to_csv(DB_FILE, index=False)
                st.rerun()

        with m2:
            st.subheader("學員檔案庫")
            edited_stu = st.data_editor(df_stu, num_rows="dynamic", use_container_width=True,
                                        column_config={"課程類別": st.column_config.SelectboxColumn(options=ALL_CATS)})
            if st.button("更新學員資料"):
                edited_stu.to_csv(STU_FILE, index=False)
                st.rerun()
            
            st.subheader("💌 學員訊息回覆")
            st.dataframe(df_req, use_container_width=True)
            if st.button("清除所有已讀訊息"):
                pd.DataFrame(columns=SCHEMA[REQ_FILE]).to_csv(REQ_FILE, index=False)
                st.rerun()

        with m3:
            st.subheader("📈 嵐教練營運報表")
            if not df_db.empty:
                df_stat = df_db.copy()
                df_stat["月份"] = pd.to_datetime(df_stat["日期"]).dt.strftime("%Y-%m")
                
                # 月份統計
                month_chart = alt.Chart(df_stat).mark_bar().encode