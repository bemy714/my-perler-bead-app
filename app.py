import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFilter
import pandas as pd
import numpy as np
import io
import math
from colors import BEAD_LIBRARY

# --- 核心運算：色彩距離與匹配 ---

def get_closest_bead(pixel_rgb, active_palette):
    """使用歐幾里得距離尋找最接近色: $$d = \sqrt{(r_1-r_2)^2 + (g_1-g_2)^2 + (b_1-b_2)^2}$$"""
    pr, pg, pb = pixel_rgb
    min_dist = float('inf')
    best_bead = active_palette[0]
    for bead in active_palette:
        dist = (pr - bead['r'])**2 + (pg - bead['g'])**2 + (pb - bead['b'])**2
        if dist < min_dist:
            min_dist = dist
            best_bead = bead
    return best_bead

def process_image(image, width_beads, use_dithering, brightness, contrast, max_colors, retro_mode):
    image = image.convert("RGB")
    if retro_mode:
        image = image.filter(ImageFilter.SHARPEN)
    
    # 影像增強
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    
    # 縮放
    w_percent = (width_beads / float(image.size[0]))
    h_beads = int((float(image.size[1]) * float(w_percent)))
    img_small = image.resize((width_beads, h_beads), Image.Resampling.LANCZOS)
    
    # PIL Quantize 限制 (處理 Pillow 的 256 色限制)
    pal_data = []
    # 這裡我們挑選色庫中前 256 個顏色作為基礎調色盤
    limited_palette = BEAD_LIBRARY[:256]
    for b in limited_palette: pal_data.extend([b['r'], b['g'], b['b']])
    pal_data.extend([0] * (768 - len(pal_data)))
    
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(pal_data)
    
    dither = Image.Dither.FLOYDSTEINBERG if use_dithering else Image.Dither.NONE
    img_quant = img_small.quantize(palette=pal_img, dither=dither).convert("RGB")
    
    return img_quant, h_beads

# --- UI 介面 ---

st.set_page_config(page_title="拼豆大師 Ultimate", layout="wide")
st.title("🏆 拼豆大師 Ultimate - 終極工作站")

with st.sidebar:
    st.header("📸 影像處理")
    file = st.file_uploader("上傳圖片", type=["png", "jpg", "jpeg"])
    bead_w = st.slider("寬度 (顆數)", 10, 150, 30)
    brightness = st.slider("亮度調整", 0.5, 2.0, 1.0)
    contrast = st.slider("對比度調整", 0.5, 2.0, 1.1)
    
    st.header("📐 拼豆規格")
    bead_size_option = st.selectbox("豆子尺寸", ["Midi (5.0mm)", "Mini (2.6mm)"])
    bead_mm = 5.0 if "5.0" in bead_size_option else 2.6
    view_mode = st.radio("預覽風格", ["標準方格", "圓形豆豆", "熨燙模擬"])
    
    st.header("🔍 進階輔助")
    retro_filter = st.checkbox("開啟 AI 復古銳化", value=True)
    dither_on = st.checkbox("開啟漸層抖動", value=True)
    board_line = st.checkbox("顯示 29x29 分界線", value=True)
    focus_color = st.selectbox("🎯 顏色追蹤", ["全部顯示"] + sorted([b['code'] for b in BEAD_LIBRARY]))

    st.header("💰 成本核算")
    price_bag = st.number_input("每包價格 (NTD)", value=60)
    qty_bag = st.number_input("每包顆數", value=1000)

if file:
    img_input = Image.open(file)
    processed, h_beads = process_image(img_input, bead_w, dither_on, brightness, contrast, 256, retro_filter)
    
    st.info(f"📏 實體尺寸預覽：約 {bead_w * bead_mm / 10:.1f} x {h_beads * bead_mm / 10:.1f} cm")

    tab1, tab2 = st.tabs(["🖼️ 專業座標圖紙", "📊 成本清單與統計"])

    with tab1:
        # 繪圖設定
        px = 35 
        offset = 40
        final_img = Image.new("RGB", (bead_w * px + offset, h_beads * px + offset), (255, 255, 255))
        draw = ImageDraw.Draw(final_img)
        
        bead_log = []
        for y in range(h_beads):
            # 繪製 Y 軸座標 (A, B, C...)
            draw.text((10, y*px + offset + 10), chr(65 + (y % 26)) + str(y // 26), fill=(100, 100, 100))
            for x in range(bead_w):
                # 繪製 X 軸座標
                if y == 0: draw.text((x*px + offset + 10, 10), str(x+1), fill=(100, 100, 100))
                
                matched = get_closest_bead(processed.getpixel((x, y)), BEAD_LIBRARY)
                bead_log.append(matched['code'])
                
                fill = (matched['r'], matched['g'], matched['b'])
                is_focused = (focus_color == "全部顯示" or matched['code'] == focus_color)
                if not is_focused: fill = (245, 245, 245)
                
                pos = [x*px + offset, y*px + offset, (x+1)*px + offset, (y+1)*px + offset]
                
                # 不同視覺風格
                if view_mode == "標準方格":
                    draw.rectangle(pos, fill=fill, outline=(230, 230, 230))
                elif view_mode == "圓形豆豆":
                    draw.ellipse([pos[0]+2, pos[1]+2, pos[2]-2, pos[3]-2], fill=fill, outline=(200, 200, 200))
                else: # 熨燙模擬
                    draw.rounded_rectangle(pos, radius=8, fill=fill)

                if is_focused and sum(fill) < 700: # 防呆背景色不顯示文字
                    t_col = (255, 255, 255) if sum(fill) < 400 else (0, 0, 0)
                    draw.text((x*px + offset + 4, y*px + offset + 10), matched['code'], fill=t_col)

        # 29x29 紅色邊界線
        if board_line:
            for i in range(0, bead_w, 29):
                draw.line([(i*px+offset, 0), (i*px+offset, h_beads*px+offset)], fill="#FF4B4B", width=2)
            for j in range(0, h_beads, 29):
                draw.line([(0, j*px+offset), (bead_w*px+offset, j*px+offset)], fill="#FF4B4B", width=2)

        st.image(final_img, use_container_width=True)
        
        # --- 下載區：正確的 PNG 編碼 ---
        buf = io.BytesIO()
        final_img.save(buf, format="PNG")
        st.download_button("💾 下載 1:1 精確圖紙 (PNG)", buf.getvalue(), "pattern.png", "image/png")

    with tab2:
        df = pd.Series(bead_log).value_counts().reset_index()
        df.columns = ['色號代碼', '所需顆數']
        df['預估包數'] = df['所需顆數'].apply(lambda x: math.ceil(x / qty_bag))
        df['成本小計'] = df['預估包數'] * price_bag
        
        st.dataframe(df, use_container_width=True)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("總豆子數", f"{len(bead_log)} 顆")
        c2.metric("預估總包數", f"{df['預估包數'].sum()} 包")
        c3.metric("總預算", f"NTD {df['成本小計'].sum()}")
        
        st.download_button("📥 下載購物清單 (CSV)", df.to_csv(index=False).encode('utf-8-sig'), "bom.csv")
else:
    st.warning("請上傳圖片。建議選用對比鮮明的圖案以獲得最佳像素效果！")