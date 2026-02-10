import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFilter
import pandas as pd
import numpy as np
import io
import math
from colors import BEAD_LIBRARY

# --- 核心邏輯 ---

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

def process_image(image, width_beads, use_dithering, brightness, contrast, saturation, max_colors, edge_boost):
    image = image.convert("RGB")
    # 影像增強
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Color(image).enhance(saturation)
    
    # 邊緣強化 (如果開啟)
    if edge_boost > 0:
        edges = image.filter(ImageFilter.FIND_EDGES).convert("L")
        edges = ImageEnhance.Brightness(edges).enhance(edge_boost)
        image = Image.composite(Image.new("RGB", image.size, (0,0,0)), image, edges)

    w_percent = (width_beads / float(image.size[0]))
    h_beads = int((float(image.size[1]) * float(w_percent)))
    img_small = image.resize((width_beads, h_beads), Image.Resampling.LANCZOS)
    
    # 限色處理
    img_temp = img_small.quantize(colors=max_colors).convert("RGB")
    unique_pixels = list(set(img_temp.getdata()))
    dynamic_palette = [get_closest_bead(p, BEAD_LIBRARY) for p in unique_pixels[:256]]
    
    pal_data = []
    for b in dynamic_palette: pal_data.extend([b['r'], b['g'], b['b']])
    pal_data.extend([0] * (768 - len(pal_data)))
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(pal_data)
    
    dither = Image.Dither.FLOYDSTEINBERG if use_dithering else Image.Dither.NONE
    img_quant = img_small.quantize(palette=pal_img, dither=dither).convert("RGB")
    
    return img_quant, h_beads

# --- UI 介面 ---

st.set_page_config(page_title="拼豆大師 Pro v3.0", layout="wide")
st.title("🏆 拼豆大師 Pro v3.0 - 全球專業版")

with st.sidebar:
    st.header("🎨 視覺風格")
    view_mode = st.radio("預覽模式", ["標準網格", "未熨燙 (圓豆)", "已熨燙 (平整)"])
    edge_boost = st.slider("邊緣描邊強化", 0.0, 5.0, 0.0)
    
    st.header("📸 影像微調")
    brightness = st.slider("亮度", 0.5, 2.0, 1.0)
    contrast = st.slider("對比", 0.5, 2.0, 1.1)
    
    st.header("🧱 拼豆規格")
    file = st.file_uploader("上傳圖片", type=["png", "jpg", "jpeg"])
    bead_w = st.slider("寬度 (顆)", 10, 150, 29)
    max_colors = st.slider("總用色上限", 2, 64, 20)
    show_symbols = st.checkbox("顯示色號標籤", value=True)
    board_line = st.checkbox("顯示 29x29 分界線", value=True)
    focus_color = st.selectbox("🎯 顏色追蹤模式", ["全部顯示"] + sorted([b['code'] for b in BEAD_LIBRARY]))

if file:
    input_img = Image.open(file)
    processed_small, h_beads = process_image(input_img, bead_w, True, brightness, contrast, 1.2, max_colors, edge_boost)
    
    st.info(f"📏 實體尺寸預估：{bead_w*0.5} x {h_beads*0.5} cm")

    tab1, tab2 = st.tabs(["🖼️ 設計圖紙", "📊 材料清單"])

    with tab1:
        px = 30 
        output_img = Image.new("RGB", (bead_w * px, h_beads * px), (255, 255, 255))
        draw = ImageDraw.Draw(output_img)
        
        bead_counts = []
        for y in range(h_beads):
            for x in range(bead_w):
                matched = get_closest_bead(processed_small.getpixel((x, y)), BEAD_LIBRARY)
                bead_counts.append(matched['code'])
                
                fill_color = (matched['r'], matched['g'], matched['b'])
                is_focused = (focus_color == "全部顯示" or matched['code'] == focus_color)
                
                if not is_focused:
                    fill_color = (240, 240, 240) # 淡化非聚焦色

                pos = [x*px, y*px, (x+1)*px, (y+1)*px]
                
                # --- 不同預覽模式的繪圖邏輯 ---
                if view_mode == "標準網格":
                    draw.rectangle(pos, fill=fill_color, outline=(220, 220, 220))
                elif view_mode == "未熨燙 (圓豆)":
                    draw.ellipse([pos[0]+2, pos[1]+2, pos[2]-2, pos[3]-2], fill=fill_color, outline=(150, 150, 150))
                else: # 已熨燙
                    # 模擬燙平後豆子變成帶圓角的正方形
                    draw.rounded_rectangle(pos, radius=8, fill=fill_color)

                if show_symbols and is_focused:
                    t_col = (255,255,255) if sum(fill_color) < 400 else (0,0,0)
                    draw.text((x*px+2, y*px+8), matched['code'], fill=t_col)

        if board_line:
            for i in range(1, math.ceil(bead_w/29)):
                draw.line([(i*29*px, 0), (i*29*px, h_beads*px)], fill="#FF4B4B", width=3)
            for j in range(1, math.ceil(h_beads/29)):
                draw.line([(0, j*29*px), (bead_w*px, j*29*px)], fill="#FF4B4B", width=3)

        st.image(output_img, use_container_width=True)
        
    with tab2:
        df = pd.Series(bead_counts).value_counts().reset_index()
        df.columns = ['色號代碼', '數量']
        st.dataframe(df, use_container_width=True)
        st.metric("總顆數", len(bead_counts))