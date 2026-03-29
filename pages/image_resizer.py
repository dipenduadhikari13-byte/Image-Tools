import io
import math

import streamlit as st
from PIL import Image
from streamlit_cropper import st_cropper

from utils.image_utils import (
    ASPECT_PRESETS,
    BG_COLOR_PRESETS,
    DPI_PRESETS,
    EXT_MAP,
    MIME_MAP,
    RESOLUTION_PRESETS,
    SUPPORTED_INPUT,
    SUPPORTED_OUTPUT,
    apply_background,
    compress_to_target,
    format_size,
    get_image_bytes,
    is_likely_valid_file_signature,
    remove_background,
)


try:
    from rembg import remove as _unused_rembg
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False


st.set_page_config(page_title="Image Resizer", page_icon="🖼️", layout="wide")

st.markdown(
    """
<style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    .size-badge {
        display: inline-block; padding: 6px 16px; border-radius: 20px;
        font-weight: 600; font-size: 1.1em; margin: 4px 0;
    }
    .size-original { background: #ff4b4b22; color: #ff4b4b; border: 1px solid #ff4b4b; }
    .size-result  { background: #00c85322; color: #00c853; border: 1px solid #00c853; }
    .metric-card {
        background: #1e1e2e; border-radius: 12px; padding: 16px;
        text-align: center; border: 1px solid #333;
    }
    .metric-label { color: #888; font-size: 0.85em; }
    .metric-value { color: #fff; font-size: 1.4em; font-weight: 700; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🖼️ Image Resizer & Compressor")
st.caption("Resize, compress, crop, and update background from a single page.")

uploaded = st.file_uploader("Upload an image", type=SUPPORTED_INPUT, key="img_upload")

if uploaded:
    raw_bytes = uploaded.getvalue()
    original_size = len(raw_bytes)
    img = Image.open(io.BytesIO(raw_bytes))
    orig_w, orig_h = img.size
    _raw_dpi = img.info.get("dpi", (72, 72))
    orig_dpi = (float(_raw_dpi[0]), float(_raw_dpi[1]))
    orig_format = img.format or uploaded.name.rsplit(".", 1)[-1].upper()
    if orig_format == "JPEG":
        orig_format = "JPG"
    orig_mode = img.mode

    st.markdown("---")
    st.subheader("📊 Original Image Info")

    cols = st.columns(6)
    gcd_val = math.gcd(orig_w, orig_h)
    info_items = [
        ("File Size", format_size(original_size)),
        ("Dimensions", f"{orig_w} × {orig_h} px"),
        ("Aspect Ratio", f"{orig_w // gcd_val}:{orig_h // gcd_val}"),
        ("Format", orig_format),
        ("DPI", f"{orig_dpi[0]:.0f} × {orig_dpi[1]:.0f}"),
        ("Color Mode", orig_mode),
    ]
    for col, (label, value) in zip(cols, info_items):
        col.markdown(
            f'<div class="metric-card"><div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

    st.image(img, caption="Original", use_container_width=True)

    st.markdown("---")
    st.subheader("⚙️ Resize & Compress Settings")

    tab_size, tab_dim, tab_res, tab_dpi, tab_crop, tab_bg = st.tabs(
        [
            "📦 Target File Size",
            "📐 Dimensions & Aspect Ratio",
            "🖥️ Resolution Presets",
            "🔍 DPI",
            "✂️ Crop",
            "🎨 Background",
        ]
    )

    with tab_size:
        size_unit = st.radio("Unit", ["KB", "MB"], horizontal=True, key="sz_unit")
        if size_unit == "MB":
            min_val = 0.01
            max_val = 100.0
            default_val = round(original_size / (1024 * 1024), 2)
            step = 0.01
        else:
            min_val = 1.0
            max_val = 10240.0
            default_val = round(original_size / 1024, 1)
            step = 5.0
        target_default = round(max(min_val, min(default_val, max_val)), 2)
        target_val = st.number_input(
            f"Desired file size ({size_unit})",
            min_value=min_val,
            max_value=max_val,
            value=target_default,
            step=step,
            key=f"target_size_{size_unit}",
        )
        enable_size_target = st.checkbox("Enable target file-size compression", value=False, key="en_sz")

    with tab_dim:
        aspect_choice = st.selectbox("Aspect ratio preset", list(ASPECT_PRESETS.keys()), key="ar_preset")
        aspect = ASPECT_PRESETS[aspect_choice]

        if aspect:
            new_w = st.number_input("Width (px)", min_value=1, value=orig_w, step=1, key="dim_w_locked")
            new_h = int(new_w * aspect[1] / aspect[0])
            st.info(f"Height auto-calculated to **{new_h} px** for {aspect_choice} ratio.")
        else:
            c1, c2 = st.columns(2)
            new_w = c1.number_input("Width (px)", min_value=1, value=orig_w, step=1, key="dim_w")
            new_h = c2.number_input("Height (px)", min_value=1, value=orig_h, step=1, key="dim_h")

        lock_ratio = st.checkbox("Lock aspect ratio (scale proportionally)", value=False, key="lock_ar")
        if lock_ratio and aspect is None:
            ratio = orig_w / orig_h
            new_h = int(new_w / ratio)
            st.info(f"Height auto-set to **{new_h} px** to maintain original ratio.")

        enable_resize = st.checkbox("Enable dimension resize", value=False, key="en_dim")

        resample_options = {
            "Lanczos (best quality)": Image.LANCZOS,
            "Bicubic": Image.BICUBIC,
            "Bilinear": Image.BILINEAR,
            "Nearest (fastest)": Image.NEAREST,
        }
        resample_name = st.selectbox("Resampling filter", list(resample_options.keys()), key="resample")
        resample_filter = resample_options[resample_name]

    with tab_res:
        res_choice = st.selectbox("Resolution preset", list(RESOLUTION_PRESETS.keys()), key="res_preset")
        res_preset = RESOLUTION_PRESETS[res_choice]

        if res_preset:
            preset_w, preset_h = res_preset
            st.success(f"Selected: **{preset_w} × {preset_h} px**")
            enable_res_preset = st.checkbox("Apply this resolution preset", value=False, key="en_res")
        else:
            preset_w, preset_h = orig_w, orig_h
            enable_res_preset = False
            st.info("Select a preset above, or use the Dimensions tab for custom sizes.")

    with tab_dpi:
        dpi_preset_choice = st.selectbox("DPI preset", list(DPI_PRESETS.keys()), key="dpi_preset")
        dpi_preset_val = DPI_PRESETS[dpi_preset_choice]

        if dpi_preset_val:
            dpi_x = dpi_preset_val
            dpi_y = dpi_preset_val
            st.success(f"Selected: **{dpi_x} DPI**")
        else:
            c1, c2 = st.columns(2)
            dpi_x = c1.number_input("Horizontal DPI", min_value=1, max_value=2400, value=int(orig_dpi[0]), step=1, key="dpi_x")
            dpi_y = c2.number_input("Vertical DPI", min_value=1, max_value=2400, value=int(orig_dpi[1]), step=1, key="dpi_y")

        enable_dpi = st.checkbox("Change DPI metadata", value=False, key="en_dpi")
        st.caption("DPI change only updates metadata (for print). It does NOT resample pixels.")

    with tab_crop:
        enable_crop = st.checkbox("Enable crop & transform", value=False, key="en_crop")

        if enable_crop:
            st.markdown(
                """
                <style>
                    .crop-toolbar {
                        display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 16px 0;
                        justify-content: center;
                    }
                    .crop-pill {
                        display: inline-block; padding: 6px 16px; border-radius: 20px;
                        font-size: 0.85em; font-weight: 600; cursor: pointer;
                        border: 1.5px solid #555; background: #1a1a2e; color: #ccc;
                        transition: all 0.15s ease;
                    }
                    .crop-pill.active { background: #ff4b4b; border-color: #ff4b4b; color: #fff; }
                    .crop-info-bar {
                        display: flex; justify-content: center; gap: 24px;
                        padding: 8px 16px; background: #111827; border-radius: 10px;
                        font-family: monospace; color: #94a3b8; font-size: 0.9em;
                        margin: 8px 0;
                    }
                    .crop-info-bar span { color: #60a5fa; font-weight: 700; }
                    .transform-btn-row {
                        display: flex; justify-content: center; gap: 8px; margin: 12px 0;
                    }
                </style>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("##### 🔄 Transform")
            tf_c1, tf_c2, tf_c3, tf_c4, tf_c5 = st.columns(5)
            with tf_c1:
                rot_left = st.button("↺ 90°", key="crop_rot_l", help="Rotate left 90°", use_container_width=True)
            with tf_c2:
                rot_right = st.button("↻ 90°", key="crop_rot_r", help="Rotate right 90°", use_container_width=True)
            with tf_c3:
                flip_h = st.button("↔ Flip H", key="crop_flip_h_btn", help="Flip horizontally", use_container_width=True)
            with tf_c4:
                flip_v = st.button("↕ Flip V", key="crop_flip_v_btn", help="Flip vertically", use_container_width=True)
            with tf_c5:
                rot_custom = st.button("⟳ Custom", key="crop_rot_custom", help="Custom rotation angle", use_container_width=True)

            if "crop_rotation" not in st.session_state:
                st.session_state.crop_rotation = 0
            if "crop_flip_h_state" not in st.session_state:
                st.session_state.crop_flip_h_state = False
            if "crop_flip_v_state" not in st.session_state:
                st.session_state.crop_flip_v_state = False
            if "crop_custom_angle" not in st.session_state:
                st.session_state.crop_custom_angle = 0

            if rot_left:
                st.session_state.crop_rotation = (st.session_state.crop_rotation - 90) % 360
                st.rerun()
            if rot_right:
                st.session_state.crop_rotation = (st.session_state.crop_rotation + 90) % 360
                st.rerun()
            if flip_h:
                st.session_state.crop_flip_h_state = not st.session_state.crop_flip_h_state
                st.rerun()
            if flip_v:
                st.session_state.crop_flip_v_state = not st.session_state.crop_flip_v_state
                st.rerun()

            if rot_custom:
                st.session_state["_show_custom_rotation"] = True

            if st.session_state.get("_show_custom_rotation", False):
                custom_angle = st.slider(
                    "Rotation angle (°)",
                    -180,
                    180,
                    st.session_state.crop_custom_angle,
                    step=1,
                    key="crop_angle_slider",
                )
                if custom_angle != st.session_state.crop_custom_angle:
                    st.session_state.crop_custom_angle = custom_angle

            transforms = []
            if st.session_state.crop_rotation != 0:
                transforms.append(f"Rotated {st.session_state.crop_rotation}°")
            if st.session_state.crop_custom_angle != 0:
                transforms.append(f"Fine-rotated {st.session_state.crop_custom_angle}°")
            if st.session_state.crop_flip_h_state:
                transforms.append("Flipped H")
            if st.session_state.crop_flip_v_state:
                transforms.append("Flipped V")
            if transforms:
                st.caption(f"Active transforms: {' · '.join(transforms)}")
                if st.button("🔄 Reset transforms", key="crop_reset_tf"):
                    st.session_state.crop_rotation = 0
                    st.session_state.crop_flip_h_state = False
                    st.session_state.crop_flip_v_state = False
                    st.session_state.crop_custom_angle = 0
                    st.session_state["_show_custom_rotation"] = False
                    st.rerun()

            crop_source = img.copy()
            if st.session_state.crop_rotation != 0:
                crop_source = crop_source.rotate(-st.session_state.crop_rotation, expand=True, resample=Image.BICUBIC)
            if st.session_state.crop_custom_angle != 0:
                crop_source = crop_source.rotate(
                    -st.session_state.crop_custom_angle,
                    expand=True,
                    resample=Image.BICUBIC,
                    fillcolor=(255, 255, 255) if crop_source.mode == "RGB" else None,
                )
            if st.session_state.crop_flip_h_state:
                crop_source = crop_source.transpose(Image.FLIP_LEFT_RIGHT)
            if st.session_state.crop_flip_v_state:
                crop_source = crop_source.transpose(Image.FLIP_TOP_BOTTOM)

            st.markdown("---")
            st.markdown("##### ✂️ Crop")

            CROP_ASPECT_PRESETS = [
                ("Free", None),
                ("1:1", (1, 1)),
                ("4:3", (4, 3)),
                ("3:4", (3, 4)),
                ("16:9", (16, 9)),
                ("9:16", (9, 16)),
                ("3:2", (3, 2)),
                ("2:3", (2, 3)),
                ("4:5", (4, 5)),
                ("5:4", (5, 4)),
                ("21:9", (21, 9)),
            ]

            ar_cols = st.columns(len(CROP_ASPECT_PRESETS))
            if "crop_aspect_idx" not in st.session_state:
                st.session_state.crop_aspect_idx = 0

            for idx, (label, _ratio) in enumerate(CROP_ASPECT_PRESETS):
                with ar_cols[idx]:
                    btn_type = "primary" if st.session_state.crop_aspect_idx == idx else "secondary"
                    if st.button(label, key=f"ar_btn_{idx}", use_container_width=True, type=btn_type):
                        st.session_state.crop_aspect_idx = idx
                        st.rerun()

            crop_aspect = CROP_ASPECT_PRESETS[st.session_state.crop_aspect_idx][1]
            crop_aspect_label = CROP_ASPECT_PRESETS[st.session_state.crop_aspect_idx][0]

            with st.expander("📱 Social media presets", expanded=False):
                SOCIAL_PRESETS = {
                    "Instagram Post (1:1)": (1, 1),
                    "Instagram Story (9:16)": (9, 16),
                    "Instagram Portrait (4:5)": (4, 5),
                    "YouTube Thumbnail (16:9)": (16, 9),
                    "Facebook Post (1.91:1)": (191, 100),
                    "Twitter Post (16:9)": (16, 9),
                    "TikTok (9:16)": (9, 16),
                    "LinkedIn Banner (4:1)": (4, 1),
                    "Pinterest Pin (2:3)": (2, 3),
                }
                social_choice = st.selectbox(
                    "Quick preset",
                    ["None"] + list(SOCIAL_PRESETS.keys()),
                    key="crop_social_preset",
                )
                if social_choice != "None":
                    crop_aspect = SOCIAL_PRESETS[social_choice]
                    crop_aspect_label = social_choice

            with st.expander("⚙️ Crop settings", expanded=False):
                s_c1, s_c2 = st.columns(2)
                with s_c1:
                    crop_box_color = st.color_picker("Box color", "#FF4B4B", key="crop_box_clr")
                    crop_stroke = st.slider("Box thickness", 1, 8, 3, key="crop_stroke_w")
                with s_c2:
                    crop_realtime = st.checkbox(
                        "Real-time preview",
                        value=True,
                        key="crop_rt",
                        help="Update as you drag. Disable for large images.",
                    )

            crop_img_input = crop_source.copy()
            if crop_img_input.mode != "RGB":
                crop_img_input = crop_img_input.convert("RGB")

            src_w, src_h = crop_img_input.size
            st.markdown(
                f'<div class="crop-info-bar">'
                f'Source: <span>{src_w} × {src_h}</span> px'
                f'&nbsp;&nbsp;|&nbsp;&nbsp;Ratio: <span>{crop_aspect_label}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

            cropped_result = st_cropper(
                crop_img_input,
                realtime_update=crop_realtime,
                box_color=crop_box_color,
                aspect_ratio=crop_aspect,
                return_type="both",
                stroke_width=crop_stroke,
                key="visual_cropper",
            )

            if isinstance(cropped_result, tuple) and len(cropped_result) == 2:
                cropped_img, crop_box = cropped_result
            else:
                cropped_img = cropped_result
                crop_box = None

            if cropped_img is not None:
                cw, ch = cropped_img.size
                box_left = int(crop_box.get("left", 0)) if crop_box else 0
                box_top = int(crop_box.get("top", 0)) if crop_box else 0
                box_w = int(crop_box.get("width", cw)) if crop_box else cw
                box_h = int(crop_box.get("height", ch)) if crop_box else ch

                st.markdown(
                    f'<div class="crop-info-bar">'
                    f'Crop: <span>{cw} × {ch}</span> px'
                    f'&nbsp;&nbsp;|&nbsp;&nbsp;Position: <span>({box_left}, {box_top})</span>'
                    f'&nbsp;&nbsp;|&nbsp;&nbsp;Size: <span>{box_w} × {box_h}</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

                with st.expander("📏 Manual crop coordinates", expanded=False):
                    st.caption("Enter exact pixel coordinates for precise cropping.")
                    mc1, mc2, mc3, mc4 = st.columns(4)
                    man_left = mc1.number_input("Left (X)", 0, src_w - 1, box_left, key="man_crop_l")
                    man_top = mc2.number_input("Top (Y)", 0, src_h - 1, box_top, key="man_crop_t")
                    man_right = mc3.number_input(
                        "Right (X)",
                        1,
                        src_w,
                        min(box_left + box_w, src_w),
                        key="man_crop_r",
                    )
                    man_bottom = mc4.number_input(
                        "Bottom (Y)",
                        1,
                        src_h,
                        min(box_top + box_h, src_h),
                        key="man_crop_b",
                    )

                    if st.button("Apply manual coordinates", key="apply_man_crop", type="primary"):
                        if man_right > man_left and man_bottom > man_top:
                            cropped_img = crop_img_input.crop((man_left, man_top, man_right, man_bottom))
                            cw, ch = cropped_img.size
                            st.success(f"Manual crop applied: **{cw} × {ch} px**")
                        else:
                            st.error("Invalid coordinates. Right must be > Left, Bottom must be > Top.")

                st.markdown("---")
                prev_c1, prev_c2 = st.columns(2)
                with prev_c1:
                    st.markdown("###### 📷 Original (transformed)")
                    st.image(crop_img_input, use_container_width=True)
                with prev_c2:
                    st.markdown(f"###### ✂️ Cropped — {cw} × {ch} px")
                    st.image(cropped_img, use_container_width=True)
            else:
                st.warning("Could not produce a crop. Try adjusting the crop box.")
                cropped_img = None
        else:
            cropped_img = None
            st.info(
                "☝ Enable **crop & transform** above to open the interactive crop tool with aspect ratios, rotation, flip, and manual coordinates."
            )

    with tab_bg:
        if not REMBG_AVAILABLE:
            st.warning("⚠️ `rembg` is not installed. Install it with `pip install rembg` to enable background features.")

        bg_choice = st.selectbox(
            "Background option",
            list(BG_COLOR_PRESETS.keys()),
            index=0,
            key="bg_choice",
            help="Remove the existing background and replace it with a solid color, transparency, or a custom image.",
        )
        bg_option = BG_COLOR_PRESETS[bg_choice]
        enable_bg = bg_option is not None

        custom_bg_color = None
        bg_upload_img = None

        if bg_option == "custom":
            picked = st.color_picker("Pick a custom background color", "#ADD8E6", key="bg_custom_color")
            custom_bg_color = tuple(int(picked.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            st.markdown(
                f'<div style="width:60px;height:60px;border-radius:8px;background:rgb{custom_bg_color};border:1px solid #555;"></div>',
                unsafe_allow_html=True,
            )
        elif bg_option == "upload":
            bg_file = st.file_uploader(
                "Upload a background image",
                type=SUPPORTED_INPUT,
                key="bg_img_upload",
            )
            if bg_file:
                bg_upload_img = Image.open(io.BytesIO(bg_file.getvalue()))
                st.image(bg_upload_img, caption="Background preview", use_container_width=True)
            else:
                st.info("Upload an image to use as the background.")
        elif bg_option == "transparent":
            st.info("Background will be removed. Output will be **PNG** with transparency.")
        elif isinstance(bg_option, tuple):
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;">'
                f'<div style="width:60px;height:60px;border-radius:8px;background:rgb{bg_option};border:1px solid #555;"></div>'
                f'<span style="font-size:1.1em;">Preview: <b>{bg_choice}</b></span></div>',
                unsafe_allow_html=True,
            )

        if enable_bg:
            st.caption("🔄 The background will be removed first, then the selected background will be applied.")

    st.markdown("---")
    st.subheader("💾 Output Settings")

    c_fmt, c_qual = st.columns(2)
    with c_fmt:
        default_idx = SUPPORTED_OUTPUT.index(orig_format) if orig_format in SUPPORTED_OUTPUT else 0
        out_format = st.selectbox("Output format", SUPPORTED_OUTPUT, index=default_idx, key="out_fmt")
    with c_qual:
        if out_format in ("PNG", "BMP", "GIF", "PPM", "ICO"):
            st.info(f"{out_format} is lossless — quality slider does not apply.")
            base_quality = 95
        else:
            base_quality = st.slider(
                "Base quality (ignored when target file-size is enabled)",
                1,
                100,
                85,
                key="base_q",
            )

    bank_safe_mode = st.checkbox(
        "Bank/Official upload safe mode",
        value=True,
        help="Forces conservative encoding to reduce invalid-format rejections on strict portals.",
        key="img_bank_safe",
    )

    if bank_safe_mode and out_format not in ("JPG", "JPEG", "PNG"):
        st.info("Safe mode works best with JPG/PNG. Output will be forced to JPG for compatibility.")
        out_format = "JPG"

    if st.button("🚀 Process Image", type="primary", key="process_btn"):
        with st.spinner("Processing..."):
            result_img = img.copy()

            if enable_bg:
                if not REMBG_AVAILABLE:
                    st.error("❌ `rembg` is not installed. Cannot process background.")
                    st.stop()
                if bg_option == "upload" and bg_upload_img is None:
                    st.error("❌ Please upload a background image.")
                    st.stop()
                with st.spinner("Removing background... (this may take a moment on first run)"):
                    fg_rgba = remove_background(result_img)
                    result_img = apply_background(fg_rgba, bg_option, custom_bg_color, bg_upload_img)
                if bg_option == "transparent":
                    out_format = "PNG"

            if enable_crop and cropped_img is not None:
                result_img = cropped_img.copy()

            if enable_res_preset and res_preset:
                result_img = result_img.resize((preset_w, preset_h), Image.LANCZOS)
            elif enable_resize and (new_w != orig_w or new_h != orig_h):
                result_img = result_img.resize((int(new_w), int(new_h)), resample_filter)

            custom_dpi = (dpi_x, dpi_y) if enable_dpi else None

            if enable_size_target:
                target_bytes = int(target_val * (1024 * 1024 if size_unit == "MB" else 1024))
                result_bytes, used_quality = compress_to_target(result_img, target_bytes, out_format, custom_dpi)
            else:
                if bank_safe_mode and out_format in ("JPG", "JPEG"):
                    base_quality = min(base_quality, 92)
                result_bytes = get_image_bytes(result_img, out_format, base_quality, custom_dpi)
                used_quality = base_quality

            if bank_safe_mode and out_format in ("JPG", "JPEG") and not is_likely_valid_file_signature(result_bytes, "jpg"):
                st.error("❌ Generated image failed JPEG signature validation.")
                st.stop()

            if bank_safe_mode and out_format == "PNG" and not is_likely_valid_file_signature(result_bytes, "png"):
                st.error("❌ Generated image failed PNG signature validation.")
                st.stop()

            result_size = len(result_bytes)
            result_pil = Image.open(io.BytesIO(result_bytes))
            res_w, res_h = result_pil.size
            _raw_res_dpi = result_pil.info.get("dpi", (72, 72))
            res_dpi = (float(_raw_res_dpi[0]), float(_raw_res_dpi[1]))
            reduction = ((original_size - result_size) / original_size) * 100 if original_size else 0

        st.markdown("---")
        st.subheader("✅ Result")

        rc = st.columns(6)
        result_info = [
            ("Original Size", f'<span class="size-badge size-original">{format_size(original_size)}</span>'),
            ("New Size", f'<span class="size-badge size-result">{format_size(result_size)}</span>'),
            ("Reduction", f"{reduction:.1f} %"),
            ("Dimensions", f"{res_w} × {res_h} px"),
            ("DPI", f"{res_dpi[0]:.0f} × {res_dpi[1]:.0f}"),
            ("Quality Used", str(used_quality)),
        ]
        for col, (label, value) in zip(rc, result_info):
            col.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div></div>',
                unsafe_allow_html=True,
            )

        lc, rc2 = st.columns(2)
        lc.image(img, caption="Original", use_container_width=True)
        rc2.image(result_bytes, caption="Processed", use_container_width=True)

        ext = EXT_MAP.get(out_format, "img")
        mime = MIME_MAP.get(out_format, "application/octet-stream")
        dl_name = uploaded.name.rsplit(".", 1)[0] + f"_resized.{ext}"
        st.download_button(
            label=f"⬇️ Download ({format_size(result_size)})",
            data=result_bytes,
            file_name=dl_name,
            mime=mime,
            type="primary",
        )
else:
    st.info("👆 Upload an image to get started.")
    st.markdown("**Supported formats:** JPG, JPEG, PNG, WEBP, BMP, TIFF, GIF, ICO, PPM, PGM, PBM, PCX, TGA, SGI, EPS, DDS")
