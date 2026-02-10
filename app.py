import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageEnhance
import pandas as pd
import numpy as np
import io
import math
from colors import BEAD_LIBRARY

# --- 1. 核心邏輯優化 ---

def get_closest_bead(pixel_rgb, active_palette):
    """從目前選用的色盤中尋找最接近色"""
    pr, pg, pb = pixel_rgb
    min_dist = float('inf')
    best_bead = active_palette[0]
    for bead in active_palette:
        dist = (pr - bead['r'])**2 + (pg - bead['g'])**2 + (pb - bead['b'])**2
        if dist < min_dist:
            min_dist = dist
            best_bead = bead
    return best_bead

def process_image(image, width_beads, use_dithering, brightness, contrast, saturation, max_colors):
    # 影像增強處理
    image = image.convert("RGB")
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Color(image).enhance(saturation)
    
    # 縮放
    w_percent = (width_beads / float(image.size[0]))
    h_beads = int((float(image.size[1]) * float(w_percent)))
    img_small = image.resize((width_beads, h_beads), Image.Resampling.LANCZOS)
    
    # 智能限色邏輯：先縮減到 max_colors 種主要顏色
    img_temp = img_small.quantize(colors=max_colors).convert("RGB")
    
    # 建立 PIL 調色盤（符合 Pillow 256 色限制）
    # 我們從 311 色中選取最匹配 img_temp 的前 256 色
    unique_pixels = list(set(img_temp.getdata()))
    dynamic_palette = []
    for p in unique_pixels[:255]: # 預留空間
        dynamic_palette.append(get_closest_bead(p, BEAD_LIBRARY))
    
    pal_data = []
    for b in dynamic_palette: pal_data.extend([b['r'], b['g'], b['b']])
    pal_data.extend([0] * (768 - len(pal_data)))
    
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(pal_data)
    
    dither = Image.Dither.FLOYDSTEINBERG if use_dithering else Image.Dither.NONE
    img_quant = img_small.quantize(palette=pal_img, dither=dither).convert("RGB")
    
    return img_quant, h_beads

# --- 2. 介面設計 ---

st.set_page_config(page_title="拼豆大師 Pro v2.0", layout="wide")
st.title("💎 拼豆大師 Pro v2.0 - 專業製圖工作站")

with st.sidebar:
    st.header("📸 影像前處理")
    brightness = st.slider("亮度 (Brightness)", 0.5, 2.0, 1.0)
    contrast = st.slider("對比 (Contrast)", 0.5, 2.0, 1.1)
    saturation = st.slider("飽和度 (Saturation)", 0.0, 2.0, 1.2)
    
    st.header("🧱 拼豆核心設定")
    file = st.file_uploader("上傳原始圖片", type=["png", "jpg", "jpeg"])
    bead_w = st.slider("作品寬度 (顆數)", 10, 150, 29)
    max_colors = st.slider("限制總用色數", 2, 64, 20)
    dither_on = st.checkbox("開啟抖動演算 (漸層細節)", value=True)
    ignore_white = st.checkbox("自動忽略純白背景 (不標註)", value=True)
    
    st.header("🔍 顯示優化")
    show_symbols = st.checkbox("顯示色號標籤", value=True)
    board_line = st.checkbox("顯示 29x29 拼板紅線", value=True)
    focus_color = st.selectbox("🎯 單色聚焦模式", ["全部顯示"] + sorted([b['code'] for b in BEAD_LIBRARY]))

if file:
    input_img = Image.open(file)
    processed_small, h_beads = process_image(input_img, bead_w, dither_on, brightness, contrast, saturation, max_colors)
    
    real_w, real_h = bead_w * 0.5, h_beads * 0.5
    st.info(f"📏 預估成品：{real_w} x {real_h} cm | 用色數：{max_colors}")

    tab1, tab2 = st.tabs(["🖼️ 專業圖紙", "📊 用量統計"])

    with tab1:
        px = 30 
        output_img = Image.new("RGB", (bead_w * px, h_beads * px), (255, 255, 255))
        draw = ImageDraw.Draw(output_img)
        
        active_counts = []
        for y in range(h_beads):
            for x in range(bead_w):
                current_rgb = processed_small.getpixel((x, y))
                matched = get_closest_bead(current_rgb, BEAD_LIBRARY)
                
                # 判斷是否為白色背景且需忽略
                is_bg = ignore_white and matched['code'] in ["A01", "H01", "H02", "T01"] and sum(current_rgb) > 700
                
                # 聚焦與著色
                fill_color = (matched['r'], matched['g'], matched['b'])
                if focus_color != "全部顯示" and matched['code'] != focus_color:
                    fill_color = (245, 245, 245) # 變淡
                elif is_bg:
                    fill_color = (255, 255, 255) # 背景純白
                else:
                    active_counts.append(matched['code'])

                pos = [x*px, y*px, (x+1)*px, (y+1)*px]
                draw.rectangle(pos, fill=fill_color, outline=(235, 235, 235))
                
                if show_symbols and not is_bg:
                    if focus_color == "全部顯示" or matched['code'] == focus_color:
                        brightness_val = sum(fill_color)
                        t_col = (255, 255, 255) if brightness_val < 400 else (0, 0, 0)
                        draw.text((x*px+2, y*px+8), matched['code'], fill=t_col)

        if board_line:
            for i in range(1, math.ceil(bead_w/29)):
                draw.line([(i*29*px, 0), (i*29*px, h_beads*px)], fill="#FF4B4B", width=3)
            for j in range(1, math.ceil(h_beads/29)):
                draw.line([(0, j*29*px), (bead_w*px, j*29*px)], fill="#FF4B4B", width=3)

        st.image(output_img, use_container_width=True)
        buf = io.BytesIO()
        output_img.save(buf, format="PNG")
        st.download_button("💾 下載高清圖紙", buf.getvalue(), "pattern_pro_v2.png")

    with tab2:
        if active_counts:
            df = pd.Series(active_counts).value_counts().reset_index()
            df.columns = ['色號代碼', '所需顆數']
            df['預覽'] = df['色號代碼'].apply(lambda c: f'#%02x%02x%02x' % tuple(next(b for b in BEAD_LIBRARY if b['code']==c).values())[1:4])
            st.dataframe(df, use_container_width=True)
            st.metric("總豆子數量 (扣除背景)", len(active_counts))