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

def process_image(image, width_beads, use_dithering, brightness, contrast):
    image = image.convert("RGB")
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    
    w_percent = (width_beads / float(image.size[0]))
    h_beads = int((float(image.size[1]) * float(w_percent)))
    img_small = image.resize((width_beads, h_beads), Image.Resampling.LANCZOS)
    
    pal_data = []
    for b in BEAD_LIBRARY[:256]: pal_data.extend([b['r'], b['g'], b['b']])
    pal_data.extend([0] * (768 - len(pal_data)))
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(pal_data)
    
    dither = Image.Dither.FLOYDSTEINBERG if use_dithering else Image.Dither.NONE
    img_quant = img_small.quantize(palette=pal_img, dither=dither).convert("RGB")
    return img_quant, h_beads

# --- UI 介面 ---

st.set_page_config(page_title="拼豆大師 Ultimate 6.0", layout="wide")
st.title("🏆 拼豆大師 Ultimate 6.0 - 專業製圖工作站")

with st.sidebar:
    st.header("📸 影像與規格")
    file = st.file_uploader("上傳圖片", type=["png", "jpg", "jpeg"])
    bead_w = st.slider("作品寬度 (顆數)", 10, 200, 29)
    zoom_scale = st.slider("🔍 圖紙縮放 (像素/顆)", 10, 60, 30) # 縮放功能
    
    st.header("🎨 風格與細節")
    view_mode = st.radio("預覽風格", ["標準方格", "圓形豆豆", "熨燙模擬"])
    show_symbols = st.checkbox("顯示色號標籤", value=True)
    show_coords = st.checkbox("顯示座標軸", value=True)
    
    st.header("🧱 拼板導航")
    board_mode = st.radio("查看方式", ["完整大圖", "分板查看 (29x29)"])
    
    st.divider()
    focus_color = st.selectbox("🎯 顏色追蹤", ["全部顯示"] + sorted([b['code'] for b in BEAD_LIBRARY]))

if file:
    img_input = Image.open(file)
    # 預設參數處理
    processed, h_beads = process_image(img_input, bead_w, True, 1.0, 1.1)
    
    # 計算拼板
    boards_w = math.ceil(bead_w / 29)
    boards_h = math.ceil(h_beads / 29)
    
    st.sidebar.info(f"🧱 拼板需求：{boards_w} x {boards_h} 塊板子")

    tab1, tab2 = st.tabs(["🖼️ 圖紙工作區", "📊 數據與採購"])

    with tab1:
        # 分板查看邏輯
        start_x, end_x = 0, bead_w
        start_y, end_y = 0, h_beads
        
        if board_mode == "分板查看 (29x29)":
            col_b1, col_b2 = st.columns(2)
            b_x = col_b1.number_input("拼板橫向位置", 1, boards_w, 1) - 1
            b_y = col_b2.number_input("拼板縱向位置", 1, boards_h, 1) - 1
            start_x, end_x = b_x * 29, min((b_x + 1) * 29, bead_w)
            start_y, end_y = b_y * 29, min((b_y + 1) * 29, h_beads)
            st.caption(f"📍 目前正在查看：第 ({b_x+1}, {b_y+1}) 塊拼板")

        # 繪圖邏輯
        px = zoom_scale # 使用 Slider 控制縮放
        offset = 40 if show_coords else 0
        current_w = end_x - start_x
        current_h = end_y - start_y
        
        final_img = Image.new("RGB", (current_w * px + offset, current_h * px + offset), (255, 255, 255))
        draw = ImageDraw.Draw(final_img)
        
        bead_log = []
        for y_idx, y in enumerate(range(start_y, end_y)):
            if show_coords:
                draw.text((10, y_idx*px + offset + (px//4)), f"{y+1}", fill=(120, 120, 120))
            
            for x_idx, x in enumerate(range(start_x, end_x)):
                if show_coords and y_idx == 0:
                    draw.text((x_idx*px + offset + (px//4), 10), f"{x+1}", fill=(120, 120, 120))
                
                matched = get_closest_bead(processed.getpixel((x, y)), BEAD_LIBRARY)
                bead_log.append(matched['code'])
                
                fill = (matched['r'], matched['g'], matched['b'])
                is_focused = (focus_color == "全部顯示" or matched['code'] == focus_color)
                if not is_focused: fill = (245, 245, 245)
                
                pos = [x_idx*px + offset, y_idx*px + offset, (x_idx+1)*px + offset, (y_idx+1)*px + offset]
                
                if view_mode == "標準方格":
                    draw.rectangle(pos, fill=fill, outline=(225, 225, 225))
                elif view_mode == "圓形豆豆":
                    draw.ellipse([pos[0]+1, pos[1]+1, pos[2]-1, pos[3]-1], fill=fill, outline=(200, 200, 200))
                else:
                    draw.rounded_rectangle(pos, radius=px//4, fill=fill)

                if show_symbols and is_focused and px > 15:
                    t_col = (255, 255, 255) if sum(fill) < 400 else (0, 0, 0)
                    draw.text((x_idx*px + offset + 2, y_idx*px + offset + (px//5)), matched['code'], fill=t_col)

        st.image(final_img, use_container_width=False) # 保持原始比例不拉伸
        
        buf = io.BytesIO()
        final_img.save(buf, format="PNG")
        st.download_button("💾 下載目前畫面 (PNG)", buf.getvalue(), "pattern.png", "image/png")

    with tab2:
        # 統計所有豆子（非僅當前查看的板子）
        all_beads = []
        for y in range(h_beads):
            for x in range(bead_w):
                m = get_closest_bead(processed.getpixel((x, y)), BEAD_LIBRARY)
                all_beads.append(m['code'])
        
        df = pd.Series(all_beads).value_counts().reset_index()
        df.columns = ['色號', '總顆數']
        st.dataframe(df, use_container_width=True)
        st.metric("整幅作品總豆子數", f"{len(all_beads)} 顆")

else:
    st.warning("請上傳圖片。你可以透過側邊欄調整『圖紙縮放』來獲得更清晰的視圖！")