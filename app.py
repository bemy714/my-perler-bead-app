import streamlit as st
from PIL import Image, ImageDraw, ImageOps
import pandas as pd
import numpy as np
import io
from colors import BEAD_LIBRARY

# --- 核心處理函式 ---

def get_closest_bead(pixel_rgb):
    """計算與全色庫中最接近的色號 (支援超過 256 色)"""
    pr, pg, pb = pixel_rgb
    min_dist = float('inf')
    best_bead = BEAD_LIBRARY[0]
    
    # 這裡會跑完所有 311 種顏色
    for bead in BEAD_LIBRARY:
        dist = (pr - bead['r'])**2 + (pg - bead['g'])**2 + (pb - bead['b'])**2
        if dist < min_dist:
            min_dist = dist
            best_bead = bead
    return best_bead

def process_image(image, width_beads, use_dithering):
    """影像像素化與色彩校正"""
    if image.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    else:
        image = image.convert("RGB")
    
    # 1. 縮放
    w_percent = (width_beads / float(image.size[0]))
    height_beads = int((float(image.size[1]) * float(w_percent)))
    img_small = image.resize((width_beads, height_beads), Image.Resampling.LANCZOS)
    
    # 2. 建立調色盤 (限制前 256 色以符合 PIL 規範)
    # 這是為了解決 ValueError: invalid palette size
    pal_data = []
    # 只取前 256 個顏色給抖動引擎使用
    limited_library = BEAD_LIBRARY[:256] 
    for bead in limited_library:
        pal_data.extend([bead['r'], bead['g'], bead['b']])
    
    # 必須精確填充到 768 個數值 (256 * 3)
    padding_needed = 768 - len(pal_data)
    if padding_needed > 0:
        pal_data.extend([0] * padding_needed)
    else:
        pal_data = pal_data[:768]
    
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(pal_data)
    
    # 3. 執行量化與抖動
    dither = Image.Dither.FLOYDSTEINBERG if use_dithering else Image.Dither.NONE
    # 這裡會先轉成 256 色的索引圖
    img_quant = img_small.quantize(palette=pal_img, dither=dither).convert("RGB")
    
    return img_quant, height_beads

# --- Streamlit 介面設計 ---

st.set_page_config(page_title="專業拼豆圖紙生成器", layout="wide")
st.title("🎨 Pro Perler Bead Designer (Fixed)")

with st.sidebar:
    st.header("🔧 設定面板")
    file = st.file_uploader("1. 上傳圖片", type=["png", "jpg", "jpeg"])
    bead_w = st.slider("2. 作品寬度 (顆數)", 10, 150, 30)
    dither_on = st.checkbox("3. 開啟抖動 (漸層更自然)", value=True)
    sym_on = st.checkbox("4. 顯示色號標籤", value=True)
    mirror_on = st.checkbox("5. 鏡像模式", value=False)
    st.divider()
    st.success(f"✅ 已成功載入全量色庫：{len(BEAD_LIBRARY)} 色")

if file:
    input_img = Image.open(file)
    if mirror_on:
        input_img = ImageOps.mirror(input_img)
    
    # 處理影像
    processed_small, h_beads = process_image(input_img, bead_w, dither_on)
    
    col_pattern, col_stats = st.columns([2, 1])
    
    with col_pattern:
        st.subheader("🖼️ 生成圖紙")
        px = 30 # 顯示格點大小
        output_img = Image.new("RGB", (bead_w * px, h_beads * px), (255, 255, 255))
        draw = ImageDraw.Draw(output_img)
        
        bead_counts = []
        
        # 逐點精確匹配全色庫
        for y in range(h_beads):
            for x in range(bead_w):
                current_pixel = processed_small.getpixel((x, y))
                # 再次匹配，這次會從 311 色中選出最精確的一種
                matched = get_closest_bead(current_pixel)
                bead_counts.append(matched['code'])
                
                # 繪圖
                pos = [x*px, y*px, (x+1)*px, (y+1)*px]
                draw.rectangle(pos, fill=(matched['r'], matched['g'], matched['b']), outline=(220, 220, 220))
                
                if sym_on:
                    brightness = (matched['r'] + matched['g'] + matched['b'])
                    t_col = (255, 255, 255) if brightness < 380 else (0, 0, 0)
                    draw.text((x*px+2, y*px+8), matched['code'], fill=t_col)

        st.image(output_img, use_container_width=True)
        
        buf = io.BytesIO()
        output_img.save(buf, format="PNG")
        st.download_button("💾 下載圖紙 (PNG)", buf.getvalue(), "perler_pattern.png", "image/png")

    with col_stats:
        st.subheader("📊 豆子用量清單")
        df = pd.Series(bead_counts).value_counts().reset_index()
        df.columns = ['色號', '顆數']
        
        def get_hex(code):
            b = next(item for item in BEAD_LIBRARY if item["code"] == code)
            return f'#%02x%02x%02x' % (b['r'], b['g'], b['b'])
        
        df['預覽'] = df['色號'].apply(get_hex)
        st.dataframe(df, use_container_width=True, height=600)
        st.metric("總顆數", len(bead_counts))
else:
    st.info("請在側邊欄上傳圖片。")