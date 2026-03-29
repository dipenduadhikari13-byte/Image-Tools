import io
import math

from PIL import Image
import pikepdf


SUPPORTED_INPUT = [
	"jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif", "gif", "ico",
	"ppm", "pgm", "pbm", "pcx", "tga", "sgi", "eps", "dds",
]

SUPPORTED_OUTPUT = ["JPG", "JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF", "ICO", "PPM"]

# Internal format name used by Pillow (JPG is saved as JPEG internally)
INTERNAL_FMT = {
	"JPG": "JPEG", "JPEG": "JPEG", "PNG": "PNG", "WEBP": "WEBP", "BMP": "BMP",
	"TIFF": "TIFF", "GIF": "GIF", "ICO": "ICO", "PPM": "PPM",
}

EXT_MAP = {
	"JPG": "jpg", "JPEG": "jpg", "PNG": "png", "WEBP": "webp", "BMP": "bmp",
	"TIFF": "tif", "GIF": "gif", "ICO": "ico", "PPM": "ppm",
}

MIME_MAP = {
	"JPG": "image/jpeg", "JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp",
	"BMP": "image/bmp", "TIFF": "image/tiff", "GIF": "image/gif",
	"ICO": "image/x-icon", "PPM": "image/x-portable-pixmap",
}

BG_COLOR_PRESETS = {
	"No Change": None,
	"No Background (Transparent)": "transparent",
	"White": (255, 255, 255),
	"Black": (0, 0, 0),
	"Light Blue": (173, 216, 230),
	"Sky Blue": (135, 206, 235),
	"Light Gray": (211, 211, 211),
	"Light Green": (144, 238, 144),
	"Light Pink": (255, 182, 193),
	"Light Yellow": (255, 255, 224),
	"Lavender": (230, 230, 250),
	"Beige": (245, 245, 220),
	"Mint": (189, 252, 201),
	"Peach": (255, 218, 185),
	"Coral": (255, 127, 80),
	"Red": (255, 0, 0),
	"Blue": (0, 0, 255),
	"Green": (0, 128, 0),
	"Custom Color": "custom",
	"Upload Background Image": "upload",
}

ASPECT_PRESETS = {
	"Free (custom)": None,
	"1:1 (Square)": (1, 1),
	"4:3 (Standard)": (4, 3),
	"3:4 (Portrait)": (3, 4),
	"16:9 (Widescreen)": (16, 9),
	"9:16 (Vertical / Reel)": (9, 16),
	"3:2 (Photo)": (3, 2),
	"2:3 (Photo Portrait)": (2, 3),
	"21:9 (Ultra-wide)": (21, 9),
	"5:4 (Large Format)": (5, 4),
	"4:5 (Instagram Portrait)": (4, 5),
	"2:1 (Panoramic)": (2, 1),
	"1:2 (Tall Banner)": (1, 2),
}

RESOLUTION_PRESETS = {
	"Custom": None,
	"HD (1280x720)": (1280, 720),
	"Full HD (1920x1080)": (1920, 1080),
	"2K (2560x1440)": (2560, 1440),
	"4K UHD (3840x2160)": (3840, 2160),
	"Instagram Post (1080x1080)": (1080, 1080),
	"Instagram Story (1080x1920)": (1080, 1920),
	"Facebook Cover (820x312)": (820, 312),
	"Twitter Header (1500x500)": (1500, 500),
	"YouTube Thumbnail (1280x720)": (1280, 720),
	"LinkedIn Banner (1584x396)": (1584, 396),
	"Passport Photo (600x600)": (600, 600),
	"A4 Print 300DPI (2480x3508)": (2480, 3508),
	"A4 Print 150DPI (1240x1754)": (1240, 1754),
	"A3 Print 300DPI (3508x4960)": (3508, 4960),
	"Letter Print 300DPI (2550x3300)": (2550, 3300),
	"Thumbnail (150x150)": (150, 150),
	"Icon (64x64)": (64, 64),
	"Favicon (32x32)": (32, 32),
}

DPI_PRESETS = {
	"Custom": None,
	"Screen (72 DPI)": 72,
	"Screen Retina (144 DPI)": 144,
	"Low Print (150 DPI)": 150,
	"Standard Print (300 DPI)": 300,
	"High Print (600 DPI)": 600,
	"Professional (1200 DPI)": 1200,
}


def format_size(size_bytes: int) -> str:
	if size_bytes < 1024:
		return f"{size_bytes} B"
	if size_bytes < 1024 * 1024:
		return f"{size_bytes / 1024:.2f} KB"
	return f"{size_bytes / (1024 * 1024):.2f} MB"


def prepare_for_format(img: Image.Image, fmt: str) -> Image.Image:
	fmt = INTERNAL_FMT.get(fmt, fmt)
	if img.mode == "CMYK":
		img = img.convert("RGB")
	if fmt in ("JPEG", "BMP", "PPM", "ICO") and img.mode in ("RGBA", "P", "LA", "PA"):
		background = Image.new("RGB", img.size, (255, 255, 255))
		if img.mode == "P":
			img = img.convert("RGBA")
		if "A" in img.mode:
			background.paste(img, mask=img.split()[-1])
		return background
	if fmt in ("JPEG", "BMP", "PPM") and img.mode not in ("RGB", "L"):
		return img.convert("RGB")
	return img


def get_image_bytes(img: Image.Image, fmt: str, quality: int, dpi: tuple | None = None) -> bytes:
	fmt = INTERNAL_FMT.get(fmt, fmt)
	buf = io.BytesIO()
	save_kwargs: dict = {"format": fmt}
	if dpi:
		save_kwargs["dpi"] = dpi
	img = prepare_for_format(img, fmt)
	if fmt == "PNG":
		save_kwargs["compress_level"] = max(0, min(9, 9 - int(quality / 11.2)))
	elif fmt == "WEBP":
		save_kwargs["quality"] = quality
		save_kwargs["method"] = 4
	elif fmt == "JPEG":
		save_kwargs["quality"] = quality
		save_kwargs["subsampling"] = 0
		save_kwargs["progressive"] = False
		save_kwargs["optimize"] = False
	elif fmt == "TIFF":
		save_kwargs["compression"] = "tiff_deflate"
	elif fmt == "ICO":
		sizes = [(min(img.width, 256), min(img.height, 256))]
		save_kwargs["sizes"] = sizes
	else:
		save_kwargs["quality"] = quality
	img.save(buf, **save_kwargs)
	return buf.getvalue()


def _binary_search_quality(img: Image.Image, target_bytes: int, fmt: str, dpi: tuple | None = None) -> tuple[bytes, int]:
	lo, hi = 1, 100
	smallest_data = get_image_bytes(img, fmt, lo, dpi)
	if len(smallest_data) > target_bytes:
		return smallest_data, lo

	best_data = smallest_data
	best_quality = lo
	for _ in range(14):
		if lo > hi:
			break
		mid = (lo + hi) // 2
		data = get_image_bytes(img, fmt, mid, dpi)
		if len(data) <= target_bytes:
			best_data = data
			best_quality = mid
			lo = mid + 1
		else:
			hi = mid - 1
	return best_data, best_quality


def compress_to_target(img: Image.Image, target_bytes: int, fmt: str, dpi: tuple | None = None) -> tuple[bytes, int]:
	real_fmt = INTERNAL_FMT.get(fmt, fmt)

	if real_fmt in ("PNG", "BMP", "GIF", "PPM", "ICO"):
		current = img.copy()
		for _ in range(20):
			data = get_image_bytes(current, fmt, 95, dpi)
			if len(data) <= target_bytes:
				return data, 95
			new_w = max(1, int(current.width * 0.8))
			new_h = max(1, int(current.height * 0.8))
			if new_w == current.width and new_h == current.height:
				break
			current = img.resize((new_w, new_h), Image.LANCZOS)
		return get_image_bytes(current, fmt, 95, dpi), 95

	hi_data = get_image_bytes(img, fmt, 100, dpi)
	if len(hi_data) <= target_bytes:
		return hi_data, 100

	data, quality = _binary_search_quality(img, target_bytes, fmt, dpi)
	if len(data) <= target_bytes:
		return data, quality

	current = img.copy()
	for _ in range(20):
		new_w = max(1, int(current.width * 0.8))
		new_h = max(1, int(current.height * 0.8))
		if new_w == current.width and new_h == current.height:
			break
		current = img.resize((new_w, new_h), Image.LANCZOS)
		data, quality = _binary_search_quality(current, target_bytes, fmt, dpi)
		if len(data) <= target_bytes:
			return data, quality
	return data, quality


def remove_background(img: Image.Image) -> Image.Image:
	from rembg import remove as rembg_remove

	buf_in = io.BytesIO()
	img.save(buf_in, format="PNG")
	buf_in.seek(0)
	buf_out = rembg_remove(buf_in.getvalue())
	return Image.open(io.BytesIO(buf_out)).convert("RGBA")


def apply_background(fg_img: Image.Image, bg_option, custom_color=None, bg_image=None) -> Image.Image:
	if bg_option == "transparent":
		return fg_img

	if bg_option == "upload" and bg_image is not None:
		bg = bg_image.convert("RGBA").resize(fg_img.size, Image.LANCZOS)
		bg.paste(fg_img, (0, 0), fg_img)
		return bg.convert("RGB")

	color = custom_color if bg_option == "custom" and custom_color else bg_option
	if not isinstance(color, tuple) or len(color) < 3:
		color = (255, 255, 255)
	bg = Image.new("RGB", fg_img.size, color[:3])
	bg.paste(fg_img, (0, 0), fg_img)
	return bg


def _jpeg_compress_image(img: Image.Image, quality: int = 85) -> Image.Image:
	buf = io.BytesIO()
	img.save(buf, format="JPEG", quality=quality, subsampling=0, progressive=False, optimize=False)
	buf.seek(0)
	return Image.open(buf).copy()


def images_to_pdf(
	images: list[Image.Image],
	page_size: str = "A4",
	orientation: str = "Auto",
	margin_mm: int = 10,
	fit_mode: str = "Fit to page",
	dpi: int = 300,
	jpeg_quality: int = 85,
	title: str = "",
) -> bytes:
	PAGE_SIZES = {
		"A4": (210, 297), "A3": (297, 420), "A5": (148, 210),
		"Letter": (216, 279), "Legal": (216, 356),
		"Fit to Image": None,
	}
	page_mm_val = PAGE_SIZES.get(page_size)
	pdf = pikepdf.Pdf.new()

	for pil_img in images:
		pil_img = pil_img.convert("RGB")
		img_w, img_h = pil_img.size

		if page_mm_val is None:
			page_w_pt = img_w / max(dpi, 1) * 72
			page_h_pt = img_h / max(dpi, 1) * 72
			final_img = pil_img
			draw_w, draw_h = page_w_pt, page_h_pt
			x_off, y_off = 0.0, 0.0
		else:
			pw_mm, ph_mm = page_mm_val
			if orientation == "Landscape":
				pw_mm, ph_mm = ph_mm, pw_mm
			elif orientation == "Auto":
				if img_w > img_h:
					pw_mm, ph_mm = max(pw_mm, ph_mm), min(pw_mm, ph_mm)
				else:
					pw_mm, ph_mm = min(pw_mm, ph_mm), max(pw_mm, ph_mm)

			page_w_pt = pw_mm * 72 / 25.4
			page_h_pt = ph_mm * 72 / 25.4
			margin_pt = margin_mm * 72 / 25.4
			usable_w_pt = page_w_pt - 2 * margin_pt
			usable_h_pt = page_h_pt - 2 * margin_pt

			img_w_pt = img_w / max(dpi, 1) * 72
			img_h_pt = img_h / max(dpi, 1) * 72

			if fit_mode == "Fit to page":
				ratio = min(usable_w_pt / max(img_w_pt, 0.1), usable_h_pt / max(img_h_pt, 0.1), 1.0)
				draw_w = img_w_pt * ratio
				draw_h = img_h_pt * ratio
				needed_w = max(int(img_w * ratio), 1)
				needed_h = max(int(img_h * ratio), 1)
				if ratio < 1.0:
					final_img = pil_img.resize((needed_w, needed_h), Image.LANCZOS)
				else:
					final_img = pil_img
				x_off = margin_pt + (usable_w_pt - draw_w) / 2
				y_off = margin_pt + (usable_h_pt - draw_h) / 2

			elif fit_mode == "Fill page (crop)":
				scale_x = usable_w_pt / max(img_w_pt, 0.1)
				scale_y = usable_h_pt / max(img_h_pt, 0.1)
				ratio = min(max(scale_x, scale_y), 2.0)
				new_w = max(int(img_w * ratio), 1)
				new_h = max(int(img_h * ratio), 1)
				resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
				crop_w = min(max(int(usable_w_pt * dpi / 72), 1), new_w)
				crop_h = min(max(int(usable_h_pt * dpi / 72), 1), new_h)
				left = (new_w - crop_w) // 2
				top = (new_h - crop_h) // 2
				final_img = resized.crop((left, top, left + crop_w, top + crop_h))
				draw_w = usable_w_pt
				draw_h = usable_h_pt
				x_off = margin_pt
				y_off = margin_pt

			else:
				target_w = max(int(usable_w_pt * dpi / 72), 1)
				target_h = max(int(usable_h_pt * dpi / 72), 1)
				final_img = pil_img.resize((target_w, target_h), Image.LANCZOS)
				draw_w = usable_w_pt
				draw_h = usable_h_pt
				x_off = margin_pt
				y_off = margin_pt

		jbuf = io.BytesIO()
		final_img.save(jbuf, format="JPEG", quality=jpeg_quality, subsampling=0, progressive=False, optimize=False)
		jpeg_data = jbuf.getvalue()

		image_obj = pikepdf.Stream(pdf, jpeg_data)
		image_obj["/Type"] = pikepdf.Name.XObject
		image_obj["/Subtype"] = pikepdf.Name.Image
		image_obj["/Width"] = final_img.width
		image_obj["/Height"] = final_img.height
		image_obj["/ColorSpace"] = pikepdf.Name.DeviceRGB
		image_obj["/BitsPerComponent"] = 8
		image_obj["/Filter"] = pikepdf.Name.DCTDecode
		image_ref = pdf.make_indirect(image_obj)

		content = f"q {draw_w:.4f} 0 0 {draw_h:.4f} {x_off:.4f} {y_off:.4f} cm /Im0 Do Q"
		content_stream = pikepdf.Stream(pdf, content.encode())

		page = pdf.add_blank_page(page_size=(page_w_pt, page_h_pt))
		page.obj["/Contents"] = pdf.make_indirect(content_stream)
		page.obj["/Resources"] = pikepdf.Dictionary({
			"/XObject": pikepdf.Dictionary({"/Im0": image_ref})
		})

	out = io.BytesIO()
	pdf.save(out)
	return out.getvalue()


def images_to_pdf_target(
	images: list[Image.Image],
	target_bytes: int,
	page_size: str = "A4",
	orientation: str = "Auto",
	margin_mm: int = 10,
	fit_mode: str = "Fit to page",
	start_dpi: int = 300,
	start_quality: int = 85,
	min_dpi: int = 72,
	min_quality: int = 35,
) -> tuple[bytes, int, int]:
	"""Best-effort target-size PDF generation from images.

	Returns:
		(pdf_bytes, used_dpi, used_quality)
	"""
	best_bytes = images_to_pdf(
		images,
		page_size=page_size,
		orientation=orientation,
		margin_mm=margin_mm,
		fit_mode=fit_mode,
		dpi=start_dpi,
		jpeg_quality=start_quality,
	)
	best_dpi = start_dpi
	best_quality = start_quality

	if len(best_bytes) <= target_bytes:
		return best_bytes, best_dpi, best_quality

	dpi_values = []
	dpi = int(start_dpi)
	while dpi >= min_dpi:
		dpi_values.append(dpi)
		next_dpi = int(dpi * 0.8)
		if next_dpi == dpi:
			break
		dpi = next_dpi

	for dpi in dpi_values:
		lo = min_quality
		hi = min(100, start_quality)
		candidate = None
		candidate_q = lo
		while lo <= hi:
			mid = (lo + hi) // 2
			pdf_bytes = images_to_pdf(
				images,
				page_size=page_size,
				orientation=orientation,
				margin_mm=margin_mm,
				fit_mode=fit_mode,
				dpi=dpi,
				jpeg_quality=mid,
			)

			if len(pdf_bytes) <= target_bytes:
				candidate = pdf_bytes
				candidate_q = mid
				lo = mid + 1
			else:
				hi = mid - 1

			if len(pdf_bytes) < len(best_bytes):
				best_bytes = pdf_bytes
				best_dpi = dpi
				best_quality = mid

		if candidate is not None:
			return candidate, dpi, candidate_q

	return best_bytes, best_dpi, best_quality


def optimize_pdf_bytes(
	pdf_bytes: bytes,
	aggressive: bool = False,
	linearize: bool = True,
) -> bytes:
	"""Optimize an existing PDF stream without rasterizing pages.

	This is a structural optimization pass. It can reduce size but may not always
	hit aggressive target thresholds for already-compressed PDFs.
	"""
	src = io.BytesIO(pdf_bytes)
	out = io.BytesIO()
	with pikepdf.Pdf.open(src) as pdf:
		save_kwargs = {
			"linearize": linearize,
			"compress_streams": True,
			"recompress_flate": True,
			"object_stream_mode": pikepdf.ObjectStreamMode.generate,
		}
		if aggressive:
			save_kwargs["min_version"] = "1.5"
		pdf.save(out, **save_kwargs)
	return out.getvalue()


def is_likely_valid_file_signature(data: bytes, kind: str) -> bool:
	"""Quick signature check for common upload formats."""
	if not data:
		return False
	kind = kind.lower()
	if kind in ("jpg", "jpeg"):
		return data.startswith(b"\xff\xd8\xff")
	if kind == "png":
		return data.startswith(b"\x89PNG\r\n\x1a\n")
	if kind == "pdf":
		return data.startswith(b"%PDF-")
	if kind == "webp":
		return len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
	return True


def merge_images(
	images: list[Image.Image],
	direction: str = "horizontal",
	alignment: str = "center",
	gap: int = 0,
	bg_color: tuple = (255, 255, 255),
	output_format: str = "JPEG",
	quality: int = 90,
) -> tuple[Image.Image, bytes]:
	imgs = [im.convert("RGB") for im in images]
	n = len(imgs)

	if direction == "horizontal":
		total_w = sum(im.width for im in imgs) + gap * (n - 1)
		max_h = max(im.height for im in imgs)
		canvas = Image.new("RGB", (total_w, max_h), bg_color)
		x = 0
		for im in imgs:
			if alignment == "top":
				y = 0
			elif alignment == "bottom":
				y = max_h - im.height
			else:
				y = (max_h - im.height) // 2
			canvas.paste(im, (x, y))
			x += im.width + gap

	elif direction == "vertical":
		max_w = max(im.width for im in imgs)
		total_h = sum(im.height for im in imgs) + gap * (n - 1)
		canvas = Image.new("RGB", (max_w, total_h), bg_color)
		y = 0
		for im in imgs:
			if alignment == "left":
				x = 0
			elif alignment == "right":
				x = max_w - im.width
			else:
				x = (max_w - im.width) // 2
			canvas.paste(im, (x, y))
			y += im.height + gap

	else:
		cols = math.ceil(math.sqrt(n))
		rows = math.ceil(n / cols)
		cell_w = max(im.width for im in imgs)
		cell_h = max(im.height for im in imgs)
		total_w = cols * cell_w + gap * (cols - 1)
		total_h = rows * cell_h + gap * (rows - 1)
		canvas = Image.new("RGB", (total_w, total_h), bg_color)
		for idx, im in enumerate(imgs):
			row, col = divmod(idx, cols)
			cx = col * (cell_w + gap) + (cell_w - im.width) // 2
			cy = row * (cell_h + gap) + (cell_h - im.height) // 2
			canvas.paste(im, (cx, cy))

	buf = io.BytesIO()
	save_fmt = INTERNAL_FMT.get(output_format, output_format)
	save_img = prepare_for_format(canvas, save_fmt)
	if save_fmt == "JPEG":
		save_img.save(buf, format="JPEG", quality=quality, subsampling=0, progressive=False, optimize=False)
	elif save_fmt == "WEBP":
		save_img.save(buf, format="WEBP", quality=quality, method=4)
	elif save_fmt == "PNG":
		save_img.save(buf, format="PNG", compress_level=6)
	else:
		save_img.save(buf, format=save_fmt)
	return canvas, buf.getvalue()


def merge_pdfs(pdf_files: list[io.BytesIO]) -> tuple[bytes, int]:
	from pypdf import PdfReader, PdfWriter

	writer = PdfWriter()
	total_pages = 0
	for pdf_data in pdf_files:
		reader = PdfReader(pdf_data)
		for page in reader.pages:
			writer.add_page(page)
			total_pages += 1
	buf = io.BytesIO()
	writer.write(buf)
	return buf.getvalue(), total_pages
