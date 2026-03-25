import streamlit as st
from pykakasi import kakasi
import pandas as pd
import os
import re
import requests

# 1. 頁面基本設定
st.set_page_config(page_title="J-Pop 學習筆記", layout="wide")
st.title("🎵 我的日文歌詞工具箱")

# --- 核心功能函式 ---
DB_FILE = "my_songs.csv"

def get_yt_title(url):
    """使用 YouTube oEmbed 接口抓取影片標題 (穩定度最高)"""
    try:
        oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        response = requests.get(oembed_url, timeout=5)
        if response.status_code == 200:
            return response.json().get('title', "未知歌曲")
        return "未知歌曲"
    except:
        return "未知歌曲"

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["YouTube 連結", "歌詞連結", "標題"])

def save_data(df):
    df.to_csv(DB_FILE, index=False, encoding="utf-8-sig")

# 初始化 Session State
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 2. 初始化日文標音工具
@st.cache_resource
def load_kakasi():
    return kakasi()

kks = load_kakasi()

# --- 功能一：歌詞標音區 ---
st.header("1. 歌詞標音 (僅限漢字)")
raw_lyrics = st.text_area("在此輸入日文歌詞：", height=200, placeholder="貼上歌詞後，只有漢字上方會標註平假名...")

if raw_lyrics:
    lines = raw_lyrics.split('\n')
    final_html_lines = []
    
    # 【深色介面樣式】
    parent_style = (
        "line-height: 3.8em; font-size: 1.4em; background-color: #1E1E1E; "
        "padding: 35px; border-radius: 15px; color: #FFFFFF; border: 1px solid #333333;"
    )
    rt_style = "font-size: 0.6em; color: #FF4B4B; vertical-align: 45%; font-weight: normal;"

    for line in lines:
        if not line.strip():
            final_html_lines.append("<br>")
            continue
            
        line_result = kks.convert(line)
        line_html = ""
        
        for item in line_result:
            orig = item['orig']
            hira = item['hira']
            
            # 【精準感應】：利用 Regex 確保只有「漢字」區塊才套用 ruby 標註
            if re.search(r'[\u4E00-\u9FFF]', orig):
                line_html += f"<ruby>{orig}<rt style='{rt_style}'>{hira}</rt></ruby>"
            else:
                line_html += orig
        
        final_html_lines.append(line_html)

    st.markdown(f"<div style='{parent_style}'>{'<br>'.join(final_html_lines)}</div>", unsafe_allow_html=True)

st.divider()

# --- 功能二：影音收藏與標題顯示 ---
st.header("2. 歌曲收藏 (自動抓取 YouTube 標題)")

with st.form("song_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        yt_input = st.text_input("YouTube 網址 (必填)")
    with c2:
        lyric_input = st.text_input("歌詞網址 (可選)")
    
    if st.form_submit_button("確認存檔"):
        if "youtube.com" in yt_input or "youtu.be" in yt_input:
            with st.spinner('獲取影片標題中...'):
                video_title = get_yt_title(yt_input)
                new_row = pd.DataFrame({
                    "YouTube 連結": [yt_input], 
                    "歌詞連結": [lyric_input], 
                    "標題": [video_title]
                })
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_data(st.session_state.df)
                st.rerun()
        else:
            st.error("請輸入正確的 YouTube 連結")

# 顯示收藏清單
if not st.session_state.df.empty:
    st.subheader("我的收藏清單")
    
    # 建立封面牆 (每行 3 個)
    cols = st.columns(3)
    
    for idx, row in st.session_state.df.iterrows():
        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', row['YouTube 連結'])
        video_id = video_id_match.group(1) if video_id_match else None
        
        with cols[idx % 3]:
            # 顯示封面圖
            if video_id:
                img_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                st.image(img_url, use_container_width=True)
            
            # 顯示抓取到的標題 (若無標題則顯示未命名)
            display_title = row['標題'] if '標題' in row and pd.notna(row['標題']) else "未命名歌曲"
            st.markdown(f"**{display_title}**")
            
            # 連結與刪除
            st.markdown(f"[📺 影片連結]({row['YouTube 連結']}) | [📄 歌詞]({row['歌詞連結']})")
            
            if st.button(f"🗑️ 刪除歌曲", key=f"del_{idx}"):
                st.session_state.df = st.session_state.df.drop(idx).reset_index(drop=True)
                save_data(st.session_state.df)
                st.rerun()

    st.divider()
    if st.button("🚨 清空所有收藏"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.session_state.df = pd.DataFrame(columns=["YouTube 連結", "歌詞連結", "標題"])
        st.rerun()