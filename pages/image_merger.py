import io

import streamlit as st
from PIL import Image

from utils.image_utils import _jpeg_compress_image, SUPPORTED_INPUT, format_size, merge_images


st.set_page_config(page_title="Image Merger", page_icon="🧩", layout="wide")

st.title("🧩 Merge Images")
st.caption("Upload 2-8 images and combine them into a single image — horizontally, vertically, or as a grid.")

merge_files = st.file_uploader(
    "Upload 2-8 images to merge",
    type=SUPPORTED_INPUT,
    accept_multiple_files=True,
    key="merge_img_upload",
)

if merge_files:
    if len(merge_files) < 2:
        st.warning("⚠️ Please upload at least 2 images to merge.")
    elif len(merge_files) > 8:
        st.warning("⚠️ Maximum 8 images. Using the first 8.")
        merge_files = merge_files[:8]

    if len(merge_files) >= 2:
        st.success(f"✅ {len(merge_files)} images ready to merge")

        preview_cols = st.columns(min(len(merge_files), 8))
        merge_pil: list[Image.Image] = []
        for idx, f in enumerate(merge_files):
            pil_img = Image.open(io.BytesIO(f.getvalue()))
            merge_pil.append(pil_img)
            with preview_cols[idx]:
                st.image(pil_img, caption=f"{idx + 1}. {f.name}", use_container_width=True)

        st.markdown("---")
        st.subheader("⚙️ Merge Settings")

        col_m1, col_m2 = st.columns(2)

        with col_m1:
            merge_direction = st.selectbox(
                "Layout",
                ["Horizontal (side by side)", "Vertical (stacked)", "Grid (auto rows/cols)"],
                key="merge_dir",
            )
            direction_map = {
                "Horizontal (side by side)": "horizontal",
                "Vertical (stacked)": "vertical",
                "Grid (auto rows/cols)": "grid",
            }
            direction_val = direction_map[merge_direction]

            if direction_val == "horizontal":
                alignment_options = ["Center", "Top", "Bottom"]
            elif direction_val == "vertical":
                alignment_options = ["Center", "Left", "Right"]
            else:
                alignment_options = ["Center"]
            merge_align = st.selectbox("Alignment", alignment_options, key="merge_align")

            merge_gap = st.slider("Gap between images (px)", 0, 100, 0, key="merge_gap")

        with col_m2:
            merge_bg = st.color_picker("Background color", "#FFFFFF", key="merge_bg")
            merge_bg_rgb = tuple(int(merge_bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))

            merge_out_fmt = st.selectbox("Output format", ["JPG", "PDF"], key="merge_fmt")
            merge_quality = 90
            if merge_out_fmt == "JPG":
                merge_quality = st.slider("Quality", 10, 100, 90, key="merge_q")

            merge_normalize = st.checkbox(
                "Resize all images to same height (horizontal) / width (vertical)",
                value=True,
                key="merge_norm",
                help="Scales images so they line up evenly.",
            )

        if st.button("🧩 Merge Images", type="primary", key="merge_btn"):
            with st.spinner("Merging images..."):
                final_imgs = list(merge_pil)
                if merge_normalize and direction_val == "horizontal":
                    target_h = min(im.height for im in final_imgs)
                    final_imgs = [
                        im.resize((int(im.width * target_h / im.height), target_h), Image.LANCZOS)
                        for im in final_imgs
                    ]
                elif merge_normalize and direction_val == "vertical":
                    target_w = min(im.width for im in final_imgs)
                    final_imgs = [
                        im.resize((target_w, int(im.height * target_w / im.width)), Image.LANCZOS)
                        for im in final_imgs
                    ]
                elif merge_normalize and direction_val == "grid":
                    target_w = min(im.width for im in final_imgs)
                    target_h = min(im.height for im in final_imgs)
                    final_imgs = [im.resize((target_w, target_h), Image.LANCZOS) for im in final_imgs]

                merged_img, merged_bytes = merge_images(
                    final_imgs,
                    direction=direction_val,
                    alignment=merge_align.lower(),
                    gap=merge_gap,
                    bg_color=merge_bg_rgb,
                    output_format=merge_out_fmt,
                    quality=merge_quality,
                )
                merged_size = len(merged_bytes)

            st.markdown("---")
            st.success(f"✅ Merged! — **{merged_img.width} × {merged_img.height} px** — **{format_size(merged_size)}**")

            st.image(merged_img, caption="Merged Result", use_container_width=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Dimensions", f"{merged_img.width} × {merged_img.height}")
            c2.metric("File Size", format_size(merged_size))
            c3.metric("Images Merged", len(final_imgs))

            if merge_out_fmt == "PDF":
                pdf_img = merged_img.convert("RGB")
                pdf_img = _jpeg_compress_image(pdf_img, merge_quality)
                pdf_buf = io.BytesIO()
                pdf_img.save(pdf_buf, format="PDF", resolution=150)
                pdf_data = pdf_buf.getvalue()
                st.download_button(
                    label=f"⬇️ Download Merged as PDF ({format_size(len(pdf_data))})",
                    data=pdf_data,
                    file_name=f"merged_{len(final_imgs)}images.pdf",
                    mime="application/pdf",
                    type="primary",
                    key="dl_merge_btn",
                )
            else:
                st.download_button(
                    label=f"⬇️ Download Merged as JPG ({format_size(merged_size)})",
                    data=merged_bytes,
                    file_name=f"merged_{len(final_imgs)}images.jpg",
                    mime="image/jpeg",
                    type="primary",
                    key="dl_merge_btn",
                )
else:
    st.info("👆 Upload 2-8 images to merge them into one.")
    st.markdown("**Supported formats:** JPG, JPEG, PNG, WEBP, BMP, TIFF, GIF, ICO, PPM, PGM, PBM, PCX, TGA, SGI, EPS, DDS")
