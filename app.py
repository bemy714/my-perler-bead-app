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
    加權歐幾里德距離公式，考慮人眼色彩生理學：
    $$d = \sqrt{2 \cdot \Delta R^2 + 4 \cdot \Delta G^2 + 3 \cdot \Delta B^2}$$
    """
    rgb = pixel[:3] # 支援 RGBA
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
    # 透明背景轉純白
    if image.mode in ('RGBA', 'LA'):
        bg = Image.new('RGB', image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[-1])
        image = bg
    else:
        image = image.convert("RGB")

    # 基礎濾鏡 (功能 1-20)
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
    ai_prompt = st.text_area("生成描述 (建議包含風格詞)", "A pixel art cute yellow creature, simple colors, white background")
    
    if st.button("🪄 Gemini AI 繪圖"):
        if not google_key:
            st.error("請提供 Google API Key")
        else:
            try:
                genai.configure(api_key=google_key)
                # 使用 2026 年標準影像生成模型呼叫
                with st.spinner("Gemini 正在為您設計拼豆圖案..."):
                    # 判斷 SDK 屬性以相容不同版本
                    if hasattr(genai, 'ImageGenerationModel'):
                        model = genai.ImageGenerationModel("imagen-3.0-generate-001")
                        result = model.generate_images(
                            prompt=f"{ai_prompt}, pixel art, flat colors, white background, centered",
                            number_of_images=1
                        )
                        st.session_state.ai_img = result.images[0]._pil_image
                    else:
                        st.error("SDK 版本不支援 ImageGenerationModel，請更新 requirements.txt")
                    
                    if st.session_state.ai_img: st.success("AI 生成成功！")
            except Exception as e:
                st.error(f"AI 生成失敗: {str(e)}")

    st.divider()
    st.header("📸 規格與處理")
    file = st.file_uploader("或上傳本地圖片", type=["png", "jpg", "jpeg"])
    bead_w = st.number_input("作品寬度 (顆數)", value=29, min_value=10)
    zoom = st.slider("圖紙縮放 (px/顆)", 10, 80, 35)

    with st.expander("🛠️ 影像微調控制"):
        br = st.slider("亮度", 0.5, 2.0, 1.0)
        ct = st.slider("對比", 0.5, 2.0, 1.1)
        sa = st.slider("飽和", 0.0, 2.0, 1.2)
        sh = st.slider("銳化", 1.0, 3.0, 1.0)
        rot = st.selectbox("旋轉", [0, 90, 180, 270])
        m_h = st.checkbox("水平鏡像")
        gray = st.checkbox("灰階模式")

    st.header("📐 顯示與導航")
    v_style = st.radio("渲染風格", ["方塊", "圓豆 (未燙)", "融合 (已燙)"], horizontal=True)
    show_axis = st.checkbox("開啟 A1/B2 座標", value=True)
    show_sym = st.checkbox("標註色號代碼", value=True)
    board_line = st.checkbox("29x29 標準板邊界", value=True)
    focus = st.selectbox("🎯 單色聚焦模式", ["全部顯示"] + sorted([b['code'] for b in BEAD_LIBRARY]))

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

    t1, t2, t3 = st.tabs(["🖼️ 專業施工圖紙", "📊 生產 BOM", "📐 物理規格"])

    with t1:
        px, off = zoom, (50 if show_axis else 0)
        out_img = Image.new("RGB", (bead_w * px + off, bead_h * px + offset if show_axis else bead_h * px), (255, 255, 255))
        # 修正高度計算
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
                elif v_style == "圓豆 (未燙)": draw.ellipse([pos[0]+2, pos[1]+2, pos[2]-2, pos[3]-2], fill=fill, outline=(180,180,180))
                else: draw.rounded_rectangle(pos, radius=px//3, fill=fill)

                if show_sym and is_focused and px > 25:
                    tc = (255,255,255) if sum(fill) < 400 else (0,0,0)
                    draw.text((x*px+off+4, y*px+off+8), matched['code'], fill=tc)

        if board_line:
            for i in range(0, bead_w, 29): draw.line([(i*px+off, 0), (i*px+off, final_h)], fill="#FF4B4B", width=2)
            for j in range(0, bead_h, 29): draw.line([(0, j*px+off), (bead_w*px+off, j*px+off)], fill="#FF4B4B", width=2)

        st.image(out_img, use_container_width=False)
        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        st.download_button("💾 下載 1:1 高清圖紙", buf.getvalue(), "perler_pattern.png", "image/png")

    with t2:
        df = pd.Series(bead_log).value_counts().reset_index()
        df.columns = ['色號代碼', '所需顆數']
        st.dataframe(df, use_container_width=True)
        st.metric("總豆子數量", len(bead_log))

    with t3:
        st.write(f"📏 **成品預估尺寸**：{bead_w * 0.5} x {bead_h * 0.5} cm")
        st.write(f"🧱 **拼板建議**：{math.ceil(bead_w/29)} x {math.ceil(bead_h/29)} 塊")
        st.write(f"⚖️ **總重量估算**：{len(bead_log) * 0.06:.1f} g")

else:
    st.info("👋 歡迎！請提供 API Key 讓 Gemini 為您設計圖案，或直接上傳圖片。")