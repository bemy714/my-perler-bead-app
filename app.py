import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFilter
import pandas as pd
import numpy as np
import io, math
from colors import BEAD_LIBRARY

# --- [1. 核心色彩演算法：精密 CIEDE 權衡] ---
def get_best_bead(pixel, palette, focus_code=None):
    rgb = pixel[:3]
    pr, pg, pb = rgb
    min_dist = float('inf')
    best = palette[0]
    
    # 權重歐幾里德距離 (對人眼更精確)
    for b in palette:
        dist = 2*(pr-b['r'])**2 + 4*(pg-b['g'])**2 + 3*(pb-b['b'])**2
        if dist < min_dist:
            min_dist = dist
            best = b
    return best

# --- [2. 影像處理引擎：濾鏡與增強] ---
def apply_advanced_filters(img, p):
    # 透明轉白 (功能 14)
    if img.mode in ('RGBA', 'LA'):
        bg = Image.new('RGB', img.size, p['bg_color'])
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")

    # 基本變換 (功能 9-12)
    if p['rot'] != 0: img = img.rotate(p['rot'], expand=True)
    if p['m_h']: img = ImageOps.mirror(img)
    if p['m_v']: img = ImageOps.flip(img)
    
    # 影像增強 (功能 1-3, 17-19)
    img = ImageEnhance.Brightness(img).enhance(p['br'])
    img = ImageEnhance.Contrast(img).enhance(p['ct'])
    img = ImageEnhance.Color(img).enhance(p['sa'])
    img = ImageEnhance.Sharpness(img).enhance(p['sh'])
    
    # 進階濾鏡 (功能 5-8)
    if p['gray']: img = ImageOps.grayscale(img).convert("RGB")
    if p['inv']: img = ImageOps.invert(img)
    if p['edge_v'] > 0:
        edges = img.filter(ImageFilter.FIND_EDGES).convert("RGB")
        img = ImageEnhance.Brightness(edges).enhance(p['edge_v'])
    
    return img

# --- [3. 介面與功能模組] ---
st.set_page_config(page_title="拼豆 Omni-Station 9.0", layout="wide")
st.title("🛡️ 拼豆大師 Omni-Station 9.0 - 旗艦工作站")

with st.sidebar:
    st.header("📸 影像實驗室 (功能 1-20)")
    file = st.file_uploader("上傳專案檔案", type=["png", "jpg", "jpeg"])
    
    with st.expander("光影與色彩增強"):
        br = st.slider("亮度", 0.1, 2.0, 1.0)
        ct = st.slider("對比", 0.1, 2.0, 1.1)
        sa = st.slider("飽和", 0.0, 2.0, 1.2)
        sh = st.slider("銳化", 1.0, 5.0, 1.0)
        bg_col = st.color_picker("背景填充色", "#FFFFFF")

    with st.expander("變換與特效"):
        rot = st.selectbox("旋轉角度", [0, 90, 180, 270])
        m_h = st.checkbox("水平鏡像")
        m_v = st.checkbox("垂直鏡像")
        gray = st.checkbox("灰階模式")
        inv = st.checkbox("負片模式")
        edge_v = st.slider("邊緣描黑強化", 0.0, 5.0, 0.0)

    st.header("🧱 色彩管理 (功能 21-40)")
    with st.expander("色盤設定"):
        max_c = st.slider("限制最高用色", 2, 128, 32)
        dither = st.checkbox("開啟漸層抖動", value=True)
        replace_target = st.selectbox("要替換的色號", ["無"] + [b['code'] for b in BEAD_LIBRARY])
        replace_to = st.selectbox("替換為", [b['code'] for b in BEAD_LIBRARY])

    st.header("📏 工程與導航 (功能 41-60)")
    bead_w = st.number_input("作品寬度 (顆)", value=29, min_value=1)
    zoom = st.slider("圖紙縮放 (px)", 10, 80, 35)
    
    with st.expander("顯示元件開關"):
        show_sym = st.checkbox("顯示色號標籤", value=True)
        show_axis = st.checkbox("顯示 A1/B2 座標", value=True)
        board_line = st.checkbox("29x29 標準板分界", value=True)
        center_mark = st.checkbox("顯示中心點標記", value=False)

    st.header("🕯️ 實體模擬 (功能 61-75)")
    v_style = st.radio("渲染模式", ["標準方格", "未熨燙 (圓豆)", "已熨燙 (平整)", "3D 陰影效果"])
    
    focus = st.selectbox("🎯 單色聚焦追蹤", ["全部顯示"] + sorted([b['code'] for b in BEAD_LIBRARY]))

if file:
    # 預處理
    img_raw = Image.open(file)
    p_dict = {'br':br, 'ct':ct, 'sa':sa, 'sh':sh, 'rot':rot, 'm_h':m_h, 'm_v':m_v, 'gray':gray, 'inv':inv, 'edge_v':edge_v, 'bg_color':bg_col}
    img_ready = apply_advanced_filters(img_raw, p_dict)
    
    # 像素化
    w_px, h_px = img_ready.size
    bead_h = int(h_px * (bead_w / w_px))
    img_small = img_ready.resize((bead_w, bead_h), Image.Resampling.LANCZOS)
    
    # 建立動態色盤
    img_temp = img_small.quantize(colors=max_c).convert("RGB")
    active_pal = [get_best_bead(p, BEAD_LIBRARY) for p in list(set(img_temp.getdata()))[:max_c]]

    tab1, tab2, tab3, tab4 = st.tabs(["🖼️ 專業施工圖紙", "📊 生產 BOM 與採購", "📐 物理尺寸", "🧪 實驗室預覽"])

    with tab1:
        # [繪圖引擎]
        px, off = zoom, (50 if show_axis else 0)
        out_img = Image.new("RGB", (bead_w * px + off, bead_h * px + off), (255, 255, 255))
        draw = ImageDraw.Draw(out_img)
        
        bead_log = []
        for y in range(bead_h):
            if show_axis: draw.text((10, y*px+off+px//4), f"{chr(65+y%26)}{y//26}", fill=(150,150,150))
            for x in range(bead_w):
                if show_axis and y == 0: draw.text((x*px+off+px//4, 10), str(x+1), fill=(150,150,150))
                
                matched = get_best_bead(img_small.getpixel((x, y)), active_pal)
                
                # 色彩替換功能
                if replace_target != "無" and matched['code'] == replace_target:
                    matched = next(b for b in BEAD_LIBRARY if b['code'] == replace_to)
                
                bead_log.append(matched['code'])
                is_f = (focus == "全部顯示" or matched['code'] == focus)
                fill = (matched['r'], matched['g'], matched['b']) if is_f else (240, 240, 240)
                
                pos = [x*px+off, y*px+off, (x+1)*px+off, (y+1)*px+off]
                
                # 實體模擬渲染 (功能 61, 62, 63)
                if v_style == "標準方格":
                    draw.rectangle(pos, fill=fill, outline=(225,225,225))
                elif v_style == "圓豆 (未燙)":
                    draw.ellipse([pos[0]+2, pos[1]+2, pos[2]-2, pos[3]-2], fill=fill, outline=(180,180,180))
                elif v_style == "已熨燙 (平整)":
                    draw.rounded_rectangle(pos, radius=px//3, fill=fill)
                else: # 3D 陰影
                    draw.rectangle(pos, fill=fill)
                    draw.line([(pos[0], pos[1]), (pos[2], pos[1])], fill=(255,255,255), width=2)
                    draw.line([(pos[0], pos[1]), (pos[0], pos[3])], fill=(255,255,255), width=2)
                
                if show_sym and is_f and px > 25:
                    tc = (255,255,255) if sum(fill) < 400 else (0,0,0)
                    draw.text((x*px+off+4, y*px+off+8), matched['code'], fill=tc)

        # 座標軸與輔助線 (功能 22, 42, 47)
        if board_line:
            for i in range(0, bead_w, 29): draw.line([(i*px+off, 0), (i*px+off, bead_h*px+off)], fill="#FF4B4B", width=2)
            for j in range(0, bead_h, 29): draw.line([(0, j*px+off), (bead_w*px+off, j*px+off)], fill="#FF4B4B", width=2)
        if center_mark:
            cx, cy = (bead_w//2)*px+off, (bead_h//2)*px+off
            draw.line([(cx-20, cy), (cx+20, cy)], fill="#00FF00", width=3)
            draw.line([(cx, cy-20), (cx, cy+20)], fill="#00FF00", width=3)

        st.image(out_img, use_container_width=False)
        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        st.download_button("💾 下載專業圖紙", buf.getvalue(), "omni_pattern.png", "image/png")

    with tab2:
        st.subheader("📊 生產採購單 (BOM)")
        df = pd.Series(bead_log).value_counts().reset_index()
        df.columns = ['色號', '顆數']
        df['預計金額'] = df['顆數'].apply(lambda x: math.ceil(x/1000) * 60)
        st.table(df)
        
        # 色彩比例圓餅圖 (功能 33)
        st.write("🎨 色彩佔比分析")
        st.bar_chart(df.set_index('色號')['顆數'])

    with tab3:
        # 功能 34, 39, 40
        c1, c2, c3 = st.columns(3)
        c1.metric("成品寬度", f"{bead_w * 0.5} cm")
        c2.metric("成品高度", f"{bead_h * 0.5} cm")
        c3.metric("總重預估", f"{len(bead_log) * 0.06:.1f} g")
        st.info(f"建議拼板：{math.ceil(bead_w/29)} x {math.ceil(bead_h/29)} 塊標準板")

    with tab4:
        st.write("🔍 實驗室功能：瞇眼測試 (功能 65)")
        st.image(img_small.filter(ImageFilter.GaussianBlur(2)), caption="距離預覽 (模擬遠看效果)")