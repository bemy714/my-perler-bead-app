import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFilter
import pandas as pd
import numpy as np
import io, math, requests
import google.generativeai as genai
from colors import BEAD_LIBRARY

# --- [1. 核心演算法：精密色彩匹配] ---
def get_best_bead(pixel, palette):
    """
    加權歐幾里德距離公式：
    $d = \sqrt{2 \cdot \Delta R^2 + 4 \cdot \Delta G^2 + 3 \cdot \Delta B^2}$
    """
    rgb = pixel[:3] # 確保支援 RGBA
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
    # 透明轉純白
    if image.mode in ('RGBA', 'LA'):
        bg = Image.new('RGB', image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[-1])
        image = bg
    else:
        image = image.convert("RGB")

    # 濾鏡處理
    if p['rot'] != 0: image = image.rotate(p['rot'], expand=True)
    if p['m_h']: image = ImageOps.mirror(image)
    image = ImageEnhance.Brightness(image).enhance(p['br'])
    image = ImageEnhance.Contrast(image).enhance(p['ct'])
    image = ImageEnhance.Color(image).enhance(p['sa'])
    if p['gray']: image = ImageOps.grayscale(image).convert("RGB")
    if p['sharp'] > 1.0: image = image.filter(ImageFilter.SHARPEN)
    
    return image

# --- [3. 介面設計] ---
st.set_page_config(page_title="拼豆 Omni-Station 11.0", layout="wide")
st.title("🛡️ 拼豆大師 Omni-Station 11.0 - Gemini AI 旗艦版")

# 初始化 AI 圖片存儲
if 'ai_img' not in st.session_state: st.session_state.ai_img = None

with st.sidebar:
    st.header("♊ Gemini AI 創意實驗室")
    google_key = st.text_input("Google API Key", type="password")
    ai_prompt = st.text_area("生成描述", "A cute yellow pikmin, pixel art, white background")
    
    if st.button("🪄 Gemini AI 繪圖"):
        if not google_key:
            st.error("🔑 請提供 API Key")
        else:
            try:
                genai.configure(api_key=google_key)
                with st.spinner("Gemini 正在調用 Imagen 3 引擎..."):
                    if hasattr(genai, 'ImageGenerationModel'):
                        model = genai.ImageGenerationModel("imagen-3.0-generate-001")
                        result = model.generate_images(
                            prompt=f"{ai_prompt}, pixel art style, flat colors, white background, centered",
                            number_of_images=1
                        )
                        st.session_state.ai_img = result.images[0]._pil_image
                        st.success("✨ AI 生成成功！")
                    else:
                        st.error("🚫 SDK 版本過舊，請更新 requirements.txt 並 Reboot App。")
            except Exception as e:
                st.error(f"❌ 發生錯誤: {str(e)}")

    st.divider()
    st.header("📸 規格與處理")
    file = st.file_uploader("或上傳本地圖片", type=["png", "jpg", "jpeg"])
    bead_w = st.number_input("作品寬度 (顆數)", value=29, min_value=10)
    zoom = st.slider("圖紙縮放 (px/顆)", 10, 100, 35)

    with st.expander("🛠️ 進階控制"):
        br = st.slider("亮度", 0.5, 2.0, 1.0)
        ct = st.slider("對比", 0.5, 2.0, 1.1)
        sa = st.slider("飽和", 0.0, 2.0, 1.2)
        sh = st.slider("銳化", 1.0, 3.0, 1.0)
        rot = st.selectbox("旋轉", [0, 90, 180, 270])
        m_h = st.checkbox("水平鏡像")
        gray = st.checkbox("灰階模式")

    st.header("📐 顯示與導航")
    v_style = st.radio("渲染風格", ["方塊", "圓豆", "熨燙模擬"], horizontal=True)
    show_axis = st.checkbox("開啟座標導航 (A1/B2)", value=True)
    show_sym = st.checkbox("標註色號代碼", value=True)
    board_line = st.checkbox("顯示 29x29 標準板界線", value=True)
    focus = st.selectbox("🎯 單色追蹤", ["全部顯示"] + sorted([b['code'] for b in BEAD_LIBRARY]))

# 決定圖片源
active_img = st.session_state.ai_img if st.session_state.ai_img else None
if file: active_img = Image.open(file)

if active_img:
    p = {'br':br, 'ct':ct, 'sa':sa, 'sharp':sh, 'rot':rot, 'm_h':m_h, 'gray':gray}
    img_ready = apply_omni_filters(active_img, p)
    
    # 像素化處理
    w_px, h_px = img_ready.size
    bead_h = int(h_px * (bead_w / w_px))
    img_small = img_ready.resize((bead_w, bead_h), Image.Resampling.LANCZOS)

    t1, t2, t3 = st.tabs(["🖼️ 專業施工圖紙", "📊 生產 BOM", "📐 物理規格分析"])

    with t1:
        px, off = zoom, (50 if show_axis else 0)
        final_h = bead_h * px + off
        out_img = Image.new("RGB", (bead_w * px + off, final_h), (255, 255, 255))
        draw = ImageDraw.Draw(out_img)
        
        bead_log = []
        for y in range(bead_h):
            if show_axis: draw.text((10, y*px+off+px//4), f"{chr(65+y%26)}{y//26}", fill=(150,150,150))
            for x in range(bead_w):
                if y == 0 and show_axis: draw.text((x*px+off+px//4, 10), str(x+1), fill=(150,150,150))
                
                matched = get_best_bead(img_small.getpixel((x, y)), BEAD_LIBRARY)
                bead_log.append(matched['code'])
                
                is_focused = (focus == "全部顯示" or matched['code'] == focus)
                fill = (matched['r'], matched['g'], matched['b']) if is_focused else (240, 240, 240)
                pos = [x*px+off, y*px+off, (x+1)*px+off, (y+1)*px+off]
                
                if v_style == "方塊": draw.rectangle(pos, fill=fill, outline=(225,225,225))
                elif v_style == "圓豆": draw.ellipse([pos[0]+2, pos[1]+2, pos[2]-2, pos[3]-2], fill=fill, outline=(180,180,180))
                else: draw.rounded_rectangle(pos, radius=px//3, fill=fill)

                if show_sym and is_focused and px > 25:
                    tc = (255,255,255) if sum(fill) < 400 else (0,0,0)
                    draw.text((x*px+off+4, y*px+off+8), matched['code'], fill=tc)

        if board_line:
            for i in range(0, bead_w, 29): draw.line([(i*px+off, 0), (i*px+off, final_h)], fill="#FF4B4B", width=2)
            for j in range(0, bead_h, 29): draw.line([(0, j*px+off), (bead_w*px+off, j*px+off)], fill="#FF4B4B", width=2)

        st.image(out_img, use_container_width=False)
        
        # 下載修正
        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        st.download_button("💾 下載高清圖紙 (PNG)", buf.getvalue(), "pattern_pro.png", "image/png")

    with t2:
        df = pd.Series(bead_log).value_counts().reset_index()
        df.columns = ['色號代碼', '所需顆數']
        st.dataframe(df, use_container_width=True)
        st.metric("總豆子需求", len(bead_log))

    with t3:
        st.write(f"📏 **成品預估尺寸**：{bead_w * 0.5} x {bead_h * 0.5} cm")
        st.write(f"🧱 **拼板建議**：{math.ceil(bead_w/29)} x {math.ceil(bead_h/29)} 塊標準板")
        st.write(f"⚖️ **成品重量**：{len(bead_log) * 0.06:.1f} g")

else:
    st.info("👋 歡迎！請提供 Google API Key 開始 AI 創作，或直接上傳圖片。")