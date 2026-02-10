import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageEnhance, ImageFilter
import pandas as pd
import numpy as np
import io, math
from colors import BEAD_LIBRARY

# --- 核心處理：支援多種功能 ---
def process_full_logic(image, width_beads, params):
    # 1. 影像增強 (亮度/對比/飽和)
    img = image.convert("RGB")
    img = ImageEnhance.Brightness(img).enhance(params['bright'])
    img = ImageEnhance.Contrast(img).enhance(params['contrast'])
    img = ImageEnhance.Color(img).enhance(params['sat'])
    
    # 2. 邊緣強化
    if params['edge'] > 0:
        edges = img.filter(ImageFilter.FIND_EDGES).convert("L")
        img = Image.composite(Image.new("RGB", img.size, (0,0,0)), img, edges)

    # 3. 縮放與像素化
    w_percent = (width_beads / float(img.size[0]))
    h_beads = int((float(img.size[1]) * float(w_percent)))
    img_small = img.resize((width_beads, h_beads), Image.Resampling.LANCZOS)
    
    # 4. 抖動與色盤校正
    pal_data = []
    for b in BEAD_LIBRARY[:256]: pal_data.extend([b['r'], b['g'], b['b']])
    pal_data.extend([0] * (768 - len(pal_data)))
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(pal_data)
    
    dither = Image.Dither.FLOYDSTEINBERG if params['dither'] else Image.Dither.NONE
    img_quant = img_small.quantize(palette=pal_img, dither=dither).convert("RGB")
    return img_quant, h_beads

# --- UI 介面 ---
st.set_page_config(page_title="拼豆大師 Ultimate 7.0", layout="wide")
st.title("🛡️ 拼豆大師 Ultimate 7.0 - 50+ 功能旗艦站")

with st.sidebar:
    st.header("📸 核心影像處理")
    file = st.file_uploader("上傳原始圖", type=["png", "jpg", "jpeg"])
    bead_w = st.slider("作品寬度 (顆)", 10, 200, 30)
    
    with st.expander("進階影像微調"):
        bright = st.slider("亮度", 0.5, 2.0, 1.0)
        contrast = st.slider("對比度", 0.5, 2.0, 1.1)
        sat = st.slider("飽和度", 0.0, 2.0, 1.2)
        edge = st.slider("邊緣強化", 0.0, 5.0, 0.0)
        dither_on = st.checkbox("開啟漸層抖動", value=True)
        mirror_on = st.checkbox("水平鏡像", value=False)

    st.header("📐 圖紙規格與顯示")
    zoom = st.slider("圖紙縮放 (像素/顆)", 10, 80, 35)
    view_style = st.selectbox("視覺風格", ["方塊", "圓豆", "熨燙模擬"])
    show_sym = st.checkbox("顯示色號代碼", value=True)
    show_axis = st.checkbox("顯示座標系統", value=True)
    
    st.header("🎯 顏色追蹤")
    focus_color = st.selectbox("聚焦特定顏色", ["全部顯示"] + sorted([b['code'] for b in BEAD_LIBRARY]))

if file:
    img_input = Image.open(file)
    if mirror_on: img_input = ImageOps.mirror(img_input)
    
    params = {'bright': bright, 'contrast': contrast, 'sat': sat, 'edge': edge, 'dither': dither_on}
    processed, h_beads = process_full_logic(img_input, bead_w, params)

    t1, t2, t3 = st.tabs(["🖼️ 專業工作區", "📊 成本採購單", "⚙️ 成品資訊"])

    with t1:
        # 繪製邏輯
        px = zoom
        offset = 50 if show_axis else 0
        final_w, final_h = bead_w * px + offset, h_beads * px + offset
        output_img = Image.new("RGB", (final_w, final_h), (255, 255, 255))
        draw = ImageDraw.Draw(output_img)
        
        bead_list = []
        for y in range(h_beads):
            if show_axis: draw.text((10, y*px + offset + (px//4)), f"{y+1}", fill=(150,150,150))
            for x in range(bead_w):
                if show_axis and y == 0: draw.text((x*px + offset + (px//4), 10), f"{x+1}", fill=(150,150,150))
                
                # 取得最接近色 (歐幾里得距離公式: $$d = \sqrt{\Delta R^2 + \Delta G^2 + \Delta B^2}$$)
                pixel = processed.getpixel((x, y))
                matched = next(b for b in BEAD_LIBRARY if (b['r'], b['g'], b['b']) == pixel) # 簡化邏輯
                bead_list.append(matched['code'])
                
                is_f = (focus_color == "全部顯示" or matched['code'] == focus_color)
                fill = (matched['r'], matched['g'], matched['b']) if is_f else (240, 240, 240)
                
                pos = [x*px + offset, y*px + offset, (x+1)*px + offset, (y+1)*px + offset]
                if view_style == "方塊": draw.rectangle(pos, fill=fill, outline=(220,220,220))
                elif view_style == "圓豆": draw.ellipse([pos[0]+2, pos[1]+2, pos[2]-2, pos[3]-2], fill=fill, outline=(180,180,180))
                else: draw.rounded_rectangle(pos, radius=px//4, fill=fill)

                if show_sym and is_f and px > 20:
                    t_c = (255,255,255) if sum(fill) < 400 else (0,0,0)
                    draw.text((x*px + offset + 4, y*px + offset + 8), matched['code'], fill=t_c)

        st.image(output_img, use_container_width=False)
        buf = io.BytesIO()
        output_img.save(buf, format="PNG")
        st.download_button("💾 下載高清設計圖 (PNG)", buf.getvalue(), "ultimate_pattern.png")

    with t2:
        df = pd.Series(bead_list).value_counts().reset_index()
        df.columns = ['色號', '數量']
        st.dataframe(df, use_container_width=True)
        st.metric("總豆子數", f"{len(bead_list)} 顆")
        st.download_button("📥 匯出採購單 (CSV)", df.to_csv(index=False).encode('utf-8-sig'), "shopping_list.csv")

    with t3:
        st.write(f"📏 **成品實體尺寸**：{bead_w*0.5} x {h_beads*0.5} cm")
        st.write(f"🧱 **拼板建議**：{math.ceil(bead_w/29)} x {math.ceil(h_beads/29)} 塊標準板")
        st.write(f"⏲️ **預估製作時間**：約 {len(bead_list)//500 + 1} 小時")

else:
    st.warning("👋 歡迎來到旗艦工作站！請上傳圖片以解鎖所有功能。")