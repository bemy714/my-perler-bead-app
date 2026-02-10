import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFilter
import pandas as pd
import numpy as np
import io, math, requests
from colors import BEAD_LIBRARY

# --- [環境診斷功能] ---
curr_version = genai.__version__

# --- [1. 核心演算法] ---
def get_best_bead(pixel, palette):
    rgb = pixel[:3]
    pr, pg, pb = rgb
    min_dist = float('inf')
    best = palette[0]
    # 加權距離：$d = \sqrt{2\Delta R^2 + 4\Delta G^2 + 3\Delta B^2}$
    for b in palette:
        dist = 2*(pr-b['r'])**2 + 4*(pg-b['g'])**2 + 3*(pb-b['b'])**2
        if dist < min_dist:
            min_dist = dist
            best = b
    return best

# --- [2. 影像處理引擎] ---
def apply_omni_filters(image, p):
    if image.mode in ('RGBA', 'LA'):
        bg = Image.new('RGB', image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[-1])
        image = bg
    else:
        image = image.convert("RGB")
    if p['rot'] != 0: image = image.rotate(p['rot'], expand=True)
    if p['m_h']: image = ImageOps.mirror(image)
    image = ImageEnhance.Brightness(image).enhance(p['br'])
    image = ImageEnhance.Contrast(image).enhance(p['ct'])
    return image

# --- [3. 介面設計] ---
st.set_page_config(page_title="拼豆 Omni-Station 11.2", layout="wide")
st.title("🛡️ 拼豆大師 Omni-Station 11.2 - 環境診斷版")

with st.sidebar:
    st.header("🧬 系統狀態")
    st.code(f"SDK 版本: {curr_version}")
    if math.tuple(map(int, curr_version.split('.'))) < (0, 8, 3):
        st.error("⚠️ 版本過低！請確認 requirements.txt 並重啟。")
    else:
        st.success("✅ 版本達標，支援 AI 繪圖。")

    st.header("♊ Gemini AI 實驗室")
    google_key = st.text_input("Google API Key", type="password")
    ai_prompt = st.text_area("生成描述", "Cute yellow creature, pixel art")
    
    if st.button("🪄 啟動 AI 生成"):
        if not google_key:
            st.error("🔑 請輸入 Key")
        else:
            try:
                genai.configure(api_key=google_key)
                with st.spinner("正在呼叫 Imagen 3..."):
                    if hasattr(genai, 'ImageGenerationModel'):
                        model = genai.ImageGenerationModel("imagen-3.0-generate-001")
                        result = model.generate_images(prompt=f"{ai_prompt}, pixel art, white background", number_of_images=1)
                        st.session_state.ai_img = result.images[0]._pil_image
                        st.success("成功！")
                    else:
                        st.error("核心組件缺失，請重新部署 App。")
            except Exception as e:
                st.error(f"錯誤: {str(e)}")

    st.header("📏 規格設定")
    file = st.file_uploader("或上傳圖片", type=["png", "jpg", "jpeg"])
    bead_w = st.number_input("寬度", value=29)
    zoom = st.slider("縮放", 10, 80, 35)

# 決定圖片源
active_img = st.session_state.get('ai_img')
if file: active_img = Image.open(file)

if active_img:
    p = {'br':1.0, 'ct':1.1, 'sa':1.2, 'rot':0, 'm_h':False, 'gray':False}
    img_ready = apply_omni_filters(active_img, p)
    
    w_px, h_px = img_ready.size
    bead_h = int(h_px * (bead_w / w_px))
    img_small = img_ready.resize((bead_w, bead_h), Image.Resampling.LANCZOS)

    t1, t2 = st.tabs(["🖼️ 施工圖紙", "📊 生產數據"])

    with t1:
        px, off = zoom, 50
        final_h = bead_h * px + off
        out_img = Image.new("RGB", (bead_w * px + off, final_h), (255, 255, 255))
        draw = ImageDraw.Draw(out_img)
        
        # 繪圖邏輯與座標標註
        for y in range(bead_h):
            draw.text((10, y*px+off+px//4), f"{chr(65+y%26)}{y//26}", fill=(150,150,150))
            for x in range(bead_w):
                if y == 0: draw.text((x*px+off+px//4, 10), str(x+1), fill=(150,150,150))
                pix = img_small.getpixel((x, y))
                m = get_best_bead(pix, BEAD_LIBRARY)
                pos = [x*px+off, y*px+off, (x+1)*px+off, (y+1)*px+off]
                draw.rectangle(pos, fill=(m['r'], m['g'], m['b']), outline=(225,225,225))
                if px > 25:
                    draw.text((x*px+off+4, y*px+off+8), m['code'], fill=(0,0,0))

        st.image(out_img)
        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        st.download_button("💾 下載圖紙", buf.getvalue(), "pattern.png", "image/png")