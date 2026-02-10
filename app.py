import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFilter
import pandas as pd
import numpy as np
import io
import math
from colors import BEAD_LIBRARY

# --- 核心運算 ---

def get_closest_bead(pixel_rgb, active_palette):
    pr, pg, pb = pixel_rgb
    min_dist = float('inf')
    best_bead = active_palette[0]
    for bead in active_palette:
        dist = (pr - bead['r'])**2 + (pg - bead['g'])**2 + (pb - bead['b'])**2
        if dist < min_dist:
            min_dist = dist
            best_bead = bead
    return best_bead

def apply_retro_filter(image):
    # 增加邊緣對比，讓像素看起來更像 8-bit 藝術
    image = image.filter(ImageFilter.SHARPEN)
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(1.2)

# --- UI 介面 ---

st.set_page_config(page_title="拼豆大師 Ultimate 5.0", layout="wide")
st.title("🏆 拼豆大師 Ultimate 5.0 - 終極製圖站")

with st.sidebar:
    st.header("📐 物理規格")
    bead_type = st.radio("拼豆類型", ["標準 (5.0mm)", "精細 (2.6mm)"])
    bead_size_mm = 5.0 if "5.0mm" in bead_type else 2.6
    
    st.header("🎨 藝術風格")
    retro_mode = st.checkbox("開啟 AI 復古風格強化", value=True)
    dither_on = st.checkbox("開啟漸層抖動", value=True)
    
    st.header("📸 影像輸入")
    file = st.file_uploader("上傳圖片", type=["png", "jpg", "jpeg"])
    bead_w = st.slider("作品寬度 (顆數)", 10, 150, 29)
    max_colors = st.slider("色彩上限", 2, 64, 25)
    
    st.header("🔍 操作輔助")
    focus_color = st.selectbox("🎯 顏色追蹤", ["全部顯示"] + sorted([b['code'] for b in BEAD_LIBRARY]))
    show_boards = st.checkbox("標註拼板分界", value=True)

if file:
    # 讀取與風格化
    img = Image.open(file).convert("RGB")
    if retro_mode:
        img = apply_retro_filter(img)
    
    # 縮放與量化
    w_percent = (bead_w / float(img.size[0]))
    h_beads = int((float(img.size[1]) * float(w_percent)))
    img_small = img.resize((bead_w, h_beads), Image.Resampling.LANCZOS)
    
    # 限色處理
    img_temp = img_small.quantize(colors=max_colors).convert("RGB")
    unique_pixels = list(set(img_temp.getdata()))
    active_palette = [get_closest_bead(p, BEAD_LIBRARY) for p in unique_pixels[:256]]
    
    # 最終匹配
    px = 30
    output_img = Image.new("RGB", (bead_w * px, h_beads * px), (255, 255, 255))
    draw = ImageDraw.Draw(output_img)
    
    bead_counts = []
    for y in range(h_beads):
        for x in range(bead_w):
            matched = get_closest_bead(img_small.getpixel((x, y)), active_palette)
            bead_counts.append(matched['code'])
            
            fill = (matched['r'], matched['g'], matched['b'])
            is_focused = (focus_color == "全部顯示" or matched['code'] == focus_color)
            if not is_focused:
                fill = (240, 240, 240)
            
            pos = [x*px, y*px, (x+1)*px, (y+1)*px]
            draw.rectangle(pos, fill=fill, outline=(220, 220, 220))
            if is_focused:
                t_col = (255,255,255) if sum(fill) < 400 else (0,0,0)
                draw.text((x*px+4, y*px+8), matched['code'], fill=t_col)

    # 繪製拼板線 (紅線)
    if show_boards:
        for i in range(0, bead_w, 29):
            draw.line([(i*px, 0), (i*px, h_beads*px)], fill="#FF4B4B", width=2)
        for j in range(0, h_beads, 29):
            draw.line([(0, j*px), (bead_w*px, j*px)], fill="#FF4B4B", width=2)

    # --- 輸出區域 ---
    t1, t2 = st.tabs(["🖼️ 圖紙預覽", "📊 用量統計"])
    
    with t1:
        st.image(output_img, use_container_width=True)
        st.download_button("💾 下載 1:1 精確圖紙", io.BytesIO(output_img.tobytes()), "pattern.png")
        st.caption(f"📏 預估實體大小：{bead_w * bead_size_mm / 10:.1f} x {h_beads * bead_size_mm / 10:.1f} cm")

    with t2:
        df = pd.Series(bead_counts).value_counts().reset_index()
        df.columns = ['色號', '顆數']
        st.dataframe(df, use_container_width=True)
        st.metric("總豆子需求", len(bead_counts))