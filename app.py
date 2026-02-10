import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageEnhance
import pandas as pd
import numpy as np
import io
import math
from fpdf import FPDF
from colors import BEAD_LIBRARY

# --- 1. 核心邏輯 ---

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

def create_pdf(output_img, bead_w, h_beads, bead_size_mm):
    """生成 1:1 比例的 PDF"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.text(10, 10, f"Perler Bead Pattern - {bead_w}x{h_beads} beads")
    
    # 計算 PDF 中的尺寸 (mm)
    img_w_mm = bead_w * bead_size_mm
    img_h_mm = h_beads * bead_size_mm
    
    # 將 PIL Image 轉為 Bytes 給 PDF
    img_byte_arr = io.BytesIO()
    output_img.save(img_byte_arr, format='PNG')
    
    # 插入圖片 (維持 1:1 物理尺寸)
    pdf.image(img_byte_arr, x=10, y=15, w=img_w_mm)
    return pdf.output()

# --- 2. 介面設計 ---

st.set_page_config(page_title="拼豆大師 Ultimate", layout="wide")
st.title("🏆 拼豆大師 Ultimate - 終極製圖工作站")

with st.sidebar:
    st.header("📦 我的收納盒 (色系篩選)")
    all_series = sorted(list(set([b['code'][0] for b in BEAD_LIBRARY])))
    selected_series = st.multiselect("勾選你擁有的色系", all_series, default=all_series)
    
    st.header("📸 影像前處理")
    brightness = st.slider("亮度", 0.5, 2.0, 1.0)
    contrast = st.slider("對比", 0.5, 2.0, 1.2)
    
    st.header("📏 規格設定")
    bead_type = st.radio("豆子直徑", ["5.0mm (標準)", "2.6mm (迷你)"])
    bead_size = 5.0 if "5.0mm" in bead_type else 2.6
    
    file = st.file_uploader("上傳圖片", type=["png", "jpg", "jpeg"])
    bead_w = st.slider("橫向顆數", 10, 150, 29)
    max_colors = st.slider("限制總用色數", 2, 64, 25)
    
    st.header("🎨 顯示調整")
    focus_color = st.selectbox("🎯 聚焦色號", ["全部顯示"] + [b['code'] for b in BEAD_LIBRARY])

# 篩選後的色庫
filtered_library = [b for b in BEAD_LIBRARY if b['code'][0] in selected_series]

if file and filtered_library:
    input_img = Image.open(file).convert("RGB")
    # 影像增強
    input_img = ImageEnhance.Brightness(input_img).enhance(brightness)
    input_img = ImageEnhance.Contrast(input_img).enhance(contrast)
    
    # 縮放與像素化
    w_percent = (bead_w / float(input_img.size[0]))
    h_beads = int((float(input_img.size[1]) * float(w_percent)))
    img_small = input_img.resize((bead_w, h_beads), Image.Resampling.LANCZOS)
    
    # 介面分欄
    tab1, tab2, tab3 = st.tabs(["🖼️ 圖紙預覽", "📋 購物清單", "