import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFilter
import pandas as pd
import numpy as np
import io, math
from colors import BEAD_LIBRARY

# --- [1. 核心演算法：精密色彩匹配] ---
def get_closest_bead(pixel, palette):
    """
    修正版：使用 [:3] 確保支援含有 Alpha 通道的圖片。
    色彩距離公式：$d = \sqrt{2\Delta R^2 + 4\Delta G^2 + 3\Delta B^2}$
    """
    rgb = pixel[:3] # 關鍵修復：只取前三碼 (R, G, B)
    pr, pg, pb = rgb
    
    min_dist = float('inf')
    best = palette[0]
    for b in palette:
        dist = 2*(pr-b['r'])**2 + 4*(pg-b['g'])**2 + 3*(pb-b['b'])**2
        if dist < min_dist:
            min_dist = dist
            best = b
    return best

# --- [2. 影像處理引擎] ---
def apply_omni_filters(image, p):
    # 透明背景轉純白處理
    if image.mode in ('RGBA', 'LA'):
        white_bg = Image.new('RGB', image.size, (255, 255, 255))
        white_bg.paste(image, mask=image.split()[-1])
        image = white_bg
    else:
        image = image.convert("RGB")

    # 鏡像與旋轉
    if p['flip_h']: image = ImageOps.mirror(image)
    if p['rotate'] != 0: image = image.rotate(p['rotate'], expand=True)
    
    # 影像增強
    image = ImageEnhance.Brightness(image).enhance(p['br'])
    image = ImageEnhance.Contrast(image).enhance(p['ct'])
    image = ImageEnhance.Color(image).enhance(p['sa'])
    
    if p['gray']: image = ImageOps.grayscale(image).convert("RGB")
    return image

# --- [3. 介面與邏輯整合] ---
st.set_page_config(page_title="拼豆 Omni-Station 8.0", layout="wide")
st.title("🛡️ 拼豆大師 Omni-Station 8.0 - 旗艦工作站")

with st.sidebar:
    st.header("📸 影像前處理")
    file = st.file_uploader("1. 上傳圖片 (支援 PNG/JPG)", type=["png", "jpg", "jpeg"])
    
    with st.expander("濾鏡與變換"):
        br = st.slider("亮度", 0.5, 2.0, 1.0)
        ct = st.slider("對比", 0.5, 2.0, 1.1)
        sa = st.slider("飽和", 0.0, 2.0, 1.2)
        rot = st.selectbox("旋轉角度", [0, 90, 180, 270])
        f_h = st.checkbox("水平鏡像")
        gray = st.checkbox("灰階模式")

    st.header("📐 規格設定")
    bead_w = st.number_input("作品寬度 (顆數)", value=29, min_value=10)
    zoom = st.slider("圖紙縮放 (px/顆)", 10, 80, 35)
    style = st.radio("視覺風格", ["標準方格", "圓形豆豆", "熨燙模擬"], horizontal=True)
    
    st.header("🎯 生產管理")
    show_sym = st.checkbox("顯示色號標籤", value=True)
    show_axis = st.checkbox("開啟座標導航", value=True)
    focus = st.selectbox("單色追蹤", ["全部顯示"] + sorted([b['code'] for b in BEAD_LIBRARY]))
    cost_bag = st.number_input("每包價格 (NTD)", value=60)

if file:
    # 1. 影像過濾
    img_raw = Image.open(file)
    p_dict = {'br':br, 'ct':ct, 'sa':sa, 'rotate':rot, 'flip_h':f_h, 'gray':gray, 'flip_v':False, 'invert':False}
    img_ready = apply_omni_filters(img_raw, p_dict)
    
    # 2. 像素化
    w_px, h_px = img_ready.size
    bead_h = int(h_px * (bead_w / w_px))
    img_small = img_ready.resize((bead_w, bead_h), Image.Resampling.LANCZOS)

    # 3. 分頁展示
    t1, t2, t3 = st.tabs(["🖼️ 專業施工圖", "📋 採購清單 (BOM)", "📐 物理資訊"])

    with t1:
        px, off = zoom, (50 if show_axis else 0)
        out_img = Image.new("RGB", (bead_w * px + off, bead_h * px + off), (255, 255, 255))
        draw = ImageDraw.Draw(out_img)
        
        bead_log = []
        for y in range(bead_h):
            if show_axis: draw.text((10, y*px+off+px//4), f"{chr(65+y%26)}{y//26}", fill=(150,150,150))
            for x in range(bead_w):
                if show_axis and y == 0: draw.text((x*px+off+px//4, 10), str(x+1), fill=(150,150,150))
                
                matched = get_closest_bead(img_small.getpixel((x, y)), BEAD_LIBRARY)
                bead_log.append(matched['code'])
                
                is_f = (focus == "全部顯示" or matched['code'] == focus)
                fill = (matched['r'], matched['g'], matched['b']) if is_f else (240, 240, 240)
                
                pos = [x*px+off, y*px+off, (x+1)*px+off, (y+1)*px+off]
                if style == "標準方格": draw.rectangle(pos, fill=fill, outline=(225,225,225))
                elif style == "圓形豆豆": draw.ellipse([pos[0]+2, pos[1]+2, pos[2]-2, pos[3]-2], fill=fill, outline=(180,180,180))
                else: draw.rounded_rectangle(pos, radius=px//3, fill=fill)
                
                if show_sym and is_f and px > 25:
                    tc = (255,255,255) if sum(fill) < 400 else (0,0,0)
                    draw.text((x*px+off+4, y*px+off+8), matched['code'], fill=tc)

        # 29x29 分界線
        for i in range(0, bead_w, 29): draw.line([(i*px+off, 0), (i*px+off, bead_h*px+off)], fill="#FF4B4B", width=2)
        for j in range(0, bead_h, 29): draw.line([(0, j*px+off), (bead_w*px+off, j*px+off)], fill="#FF4B4B", width=2)

        st.image(out_img, use_container_width=False)
        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        st.download_button("💾 下載專業施工圖", buf.getvalue(), "pattern_pro.png", "image/png")

    with t2:
        df = pd.Series(bead_log).value_counts().reset_index()
        df.columns = ['色號', '所需顆數']
        df['預估成本'] = df['所需顆數'].apply(lambda x: math.ceil(x/1000) * cost_bag)
        st.table(df)
        st.metric("總預算估計", f"NTD {df['預估成本'].sum()}")

    with t3:
        st.write(f"📏 **成品尺寸**：{bead_w*0.5} x {bead_h*0.5} cm")
        st.write(f"🧱 **拼板建議**：{math.ceil(bead_w/29)} x {math.ceil(bead_h/29)} 塊標準板")
        st.write(f"⚖️ **總重預估**：{len(bead_log)*0.06:.1f} g")

else:
    st.info("👋 歡迎！請上傳圖片以啟動 Omni-Station 功能。")