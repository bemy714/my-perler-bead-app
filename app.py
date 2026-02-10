import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFilter
import pandas as pd
import numpy as np
import io, math, requests
from colors import BEAD_LIBRARY
# 若要使用 OpenAI，需 import openai
# from openai import OpenAI 

# --- [核心演算法：精密色彩匹配] ---
def get_best_bead(pixel, palette):
    rgb = pixel[:3]
    pr, pg, pb = rgb
    min_dist = float('inf')
    best = palette[0]
    for b in palette:
        dist = 2*(pr-b['r'])**2 + 4*(pg-b['g'])**2 + 3*(pb-b['b'])**2
        if dist < min_dist:
            min_dist = dist
            best = b
    return best

# --- [AI 生成邏輯] ---
def generate_ai_art(prompt, api_key, style_preset):
    # 這是一個示意邏輯，實際部署需填入 API Key
    # 使用 OpenAI DALL-E 3 範例
    full_prompt = f"{prompt}, {style_preset}, perler bead pattern, clean flat colors, white background"
    # client = OpenAI(api_key=api_key)
    # response = client.images.generate(model="dall-e-3", prompt=full_prompt, n=1, size="1024x1024")
    # return response.data[0].url
    return None # 預設回傳 None，待使用者填入 Key

# --- [影像處理引擎] ---
def apply_advanced_filters(img, p):
    if img.mode in ('RGBA', 'LA'):
        bg = Image.new('RGB', img.size, p['bg_color'])
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    if p['rot'] != 0: img = img.rotate(p['rot'], expand=True)
    if p['m_h']: img = ImageOps.mirror(img)
    img = ImageEnhance.Brightness(img).enhance(p['br'])
    img = ImageEnhance.Contrast(img).enhance(p['ct'])
    img = ImageEnhance.Color(img).enhance(p['sa'])
    if p['gray']: img = ImageOps.grayscale(img).convert("RGB")
    return img

# --- [介面設計] ---
st.set_page_config(page_title="拼豆 Omni-Station 10.0", layout="wide")
st.title("🛡️ 拼豆大師 Omni-Station 10.0 - AI 創世紀版")

# 初始化 Session State 用於存儲 AI 生成的圖片
if 'ai_img' not in st.session_state: st.session_state.ai_img = None

with st.sidebar:
    st.header("🤖 AI 創意實驗室")
    ai_key = st.text_input("輸入 OpenAI API Key", type="password")
    ai_prompt = st.text_area("想要生成什麼？", placeholder="例如：可愛的藍色獨角獸")
    ai_style = st.selectbox("AI 風格", ["Pixel Art", "Flat Vector", "8-bit Game", "Anime Chibi"])
    
    if st.button("🪄 開始 AI 生成"):
        if ai_key and ai_prompt:
            with st.spinner("AI 正在繪圖中..."):
                # 這裡調用 AI API (此處為模擬邏輯)
                st.warning("API 調用已準備就緒，請在代碼中取消 OpenAI 註解並填入 Key。")
                # url = generate_ai_art(ai_prompt, ai_key, ai_style)
                # st.session_state.ai_img = Image.open(requests.get(url, stream=True).raw)
        else:
            st.error("請提供 API Key 與提示詞")

    st.divider()
    st.header("📸 影像輸入")
    file = st.file_uploader("或上傳現有檔案", type=["png", "jpg", "jpeg"])
    
    # 決定當前使用的圖片源
    source_img = None
    if file: source_img = Image.open(file)
    elif st.session_state.ai_img: source_img = st.session_state.ai_img

    with st.expander("🛠️ 進階前處理參數"):
        br = st.slider("亮度", 0.1, 2.0, 1.0)
        ct = st.slider("對比", 0.1, 2.0, 1.1)
        sa = st.slider("飽和", 0.0, 2.0, 1.2)
        rot = st.selectbox("旋轉角度", [0, 90, 180, 270])
        m_h = st.checkbox("水平鏡像")
        gray = st.checkbox("灰階模式")
        bg_col = st.color_picker("背景填充色", "#FFFFFF")

    st.header("📐 工程規格")
    bead_w = st.number_input("作品寬度 (顆)", value=29)
    zoom = st.slider("畫布縮放", 10, 80, 35)
    v_style = st.radio("渲染模式", ["標準方格", "圓豆", "熨燙模擬"])

if source_img:
    p_dict = {'br':br, 'ct':ct, 'sa':sa, 'rot':rot, 'm_h':m_h, 'gray':gray, 'bg_color':bg_col}
    img_ready = apply_advanced_filters(source_img, p_dict)
    
    w_px, h_px = img_ready.size
    bead_h = int(h_px * (bead_w / w_px))
    img_small = img_ready.resize((bead_w, bead_h), Image.Resampling.LANCZOS)
    
    t1, t2, t3 = st.tabs(["🖼️ 專業施工圖紙", "📊 數據清單", "📐 物理規格"])

    with t1:
        px, off = zoom, 50
        out_img = Image.new("RGB", (bead_w * px + off, bead_h * px + off), (255, 255, 255))
        draw = ImageDraw.Draw(out_img)
        
        bead_log = []
        for y in range(bead_h):
            draw.text((10, y*px+off+px//4), f"{chr(65+y%26)}{y//26}", fill=(150,150,150))
            for x in range(bead_w):
                if y == 0: draw.text((x*px+off+px//4, 10), str(x+1), fill=(150,150,150))
                matched = get_best_bead(img_small.getpixel((x, y)), BEAD_LIBRARY)
                bead_log.append(matched['code'])
                fill = (matched['r'], matched['g'], matched['b'])
                pos = [x*px+off, y*px+off, (x+1)*px+off, (y+1)*px+off]
                
                if v_style == "標準方格": draw.rectangle(pos, fill=fill, outline=(225,225,225))
                elif v_style == "圓豆": draw.ellipse([pos[0]+2, pos[1]+2, pos[2]-2, pos[3]-2], fill=fill, outline=(180,180,180))
                else: draw.rounded_rectangle(pos, radius=px//3, fill=fill)
                
                if px > 25:
                    tc = (255,255,255) if sum(fill) < 400 else (0,0,0)
                    draw.text((x*px+off+4, y*px+off+8), matched['code'], fill=tc)

        st.image(out_img, use_container_width=False)
        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        st.download_button("💾 下載 AI 拼豆圖紙", buf.getvalue(), "ai_perler.png", "image/png")

    with t2:
        df = pd.Series(bead_log).value_counts().reset_index()
        df.columns = ['色號', '顆數']
        st.dataframe(df, use_container_width=True)
        st.metric("總顆數", len(bead_log))

else:
    st.info("👋 歡迎！您可以『上傳圖片』或使用左側的『AI 創意實驗室』直接生成全新設計。")