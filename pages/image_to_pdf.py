import io

import streamlit as st
from PIL import Image

from utils.image_utils import (
    SUPPORTED_INPUT,
    format_size,
    images_to_pdf,
    images_to_pdf_target,
    is_likely_valid_file_signature,
)


st.set_page_config(page_title="Image to PDF", page_icon="📄", layout="wide")

st.title("📄 Image to PDF Converter")
st.caption("Upload one or more images and convert them into a single PDF document.")

pdf_images = st.file_uploader(
    "Upload images (multiple allowed)",
    type=SUPPORTED_INPUT,
    accept_multiple_files=True,
    key="pdf_img_upload",
    help="Upload images in the order you want them in the PDF. Drag to reorder.",
)

if pdf_images:
    st.success(f"✅ {len(pdf_images)} image(s) uploaded")

    preview_cols = st.columns(min(6, len(pdf_images)))
    pil_images: list[Image.Image] = []
    for idx, f in enumerate(pdf_images):
        pil_img = Image.open(io.BytesIO(f.getvalue()))
        pil_images.append(pil_img)
        with preview_cols[idx % len(preview_cols)]:
            st.image(pil_img, caption=f.name, use_container_width=True)

    st.markdown("---")
    st.subheader("⚙️ PDF Settings")

    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        page_size = st.selectbox("Page Size", ["A4", "A3", "A5", "Letter", "Legal", "Fit to Image"], key="pdf_page")
        orientation = st.selectbox("Orientation", ["Auto", "Portrait", "Landscape"], key="pdf_orient")

    with col_p2:
        fit_mode = st.selectbox("Image Fitting", ["Fit to page", "Fill page (crop)", "Stretch"], key="pdf_fit")
        margin_mm = st.slider("Margin (mm)", 0, 50, 10, key="pdf_margin")

    with col_p3:
        pdf_dpi = st.selectbox(
            "PDF Resolution",
            [72, 150, 300, 600],
            index=1,
            key="pdf_dpi",
            help="Lower = smaller file. 150 DPI is good for screen, 300 for print.",
        )
        pdf_quality = st.slider(
            "JPEG Quality",
            10,
            100,
            80,
            key="pdf_quality",
            help="Lower = smaller file. 70-85 is a good balance.",
        )
        pdf_title = st.text_input("PDF Title (optional)", key="pdf_title")

    st.markdown("---")
    st.subheader("🎯 Size & Compliance")

    c_s1, c_s2 = st.columns(2)
    with c_s1:
        enable_target = st.checkbox("Enable target PDF size", value=False, key="pdf_enable_target")
        target_unit = st.radio("Target unit", ["KB", "MB"], horizontal=True, key="pdf_target_unit")
        if target_unit == "MB":
            target_size = st.number_input("Target size (MB)", min_value=0.05, max_value=200.0, value=1.0, step=0.05)
            target_bytes = int(target_size * 1024 * 1024)
        else:
            target_size = st.number_input("Target size (KB)", min_value=10.0, max_value=200000.0, value=500.0, step=10.0)
            target_bytes = int(target_size * 1024)

    with c_s2:
        bank_safe_mode = st.checkbox(
            "Bank/Official upload safe mode",
            value=True,
            help="Uses conservative PDF settings and validates output signature before download.",
            key="pdf_bank_safe",
        )

    total_original = sum(len(f.getvalue()) for f in pdf_images)
    st.caption(f"📊 Total original image size: **{format_size(total_original)}**")

    if st.button("📄 Generate PDF", type="primary", key="gen_pdf_btn"):
        with st.spinner("Creating PDF..."):
            if bank_safe_mode:
                # Conservative defaults for stricter validators
                if pdf_dpi > 300:
                    pdf_dpi = 300
                if pdf_quality > 90:
                    pdf_quality = 90

            if enable_target:
                pdf_bytes, used_dpi, used_quality = images_to_pdf_target(
                    pil_images,
                    target_bytes=target_bytes,
                    page_size=page_size,
                    orientation=orientation,
                    margin_mm=margin_mm,
                    fit_mode=fit_mode,
                    start_dpi=pdf_dpi,
                    start_quality=pdf_quality,
                )
            else:
                pdf_bytes = images_to_pdf(
                    pil_images,
                    page_size=page_size,
                    orientation=orientation,
                    margin_mm=margin_mm,
                    fit_mode=fit_mode,
                    dpi=pdf_dpi,
                    jpeg_quality=pdf_quality,
                    title=pdf_title,
                )
                used_dpi = pdf_dpi
                used_quality = pdf_quality

            pdf_size = len(pdf_bytes)

        if not is_likely_valid_file_signature(pdf_bytes, "pdf"):
            st.error("❌ Generated file does not look like a valid PDF stream.")
            st.stop()

        st.markdown("---")
        st.success(f"✅ PDF created — **{len(pil_images)} page(s)** — **{format_size(pdf_size)}**")

        c1, c2, c3 = st.columns(3)
        c1.metric("Pages", len(pil_images))
        c2.metric("File Size", format_size(pdf_size))
        c3.metric("Resolution", f"{used_dpi} DPI")

        if enable_target:
            st.caption(f"Used JPEG quality: {used_quality}. Requested target: {format_size(target_bytes)}")
            if pdf_size > target_bytes:
                st.warning("Could not exactly hit target size with quality/DPI reduction. Returned closest valid output.")

        dl_name = pdf_title.strip().replace(" ", "_") if pdf_title.strip() else "images_converted"
        st.download_button(
            label=f"⬇️ Download PDF ({format_size(pdf_size)})",
            data=pdf_bytes,
            file_name=f"{dl_name}.pdf",
            mime="application/pdf",
            type="primary",
            key="dl_pdf_btn",
        )
else:
    st.info("👆 Upload one or more images to convert to PDF.")
    st.markdown("**Supported formats:** JPG, JPEG, PNG, WEBP, BMP, TIFF, GIF, ICO, PPM, PGM, PBM, PCX, TGA, SGI, EPS, DDS")
