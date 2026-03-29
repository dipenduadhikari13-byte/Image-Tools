# 🖼️ Image Tools — Fast, Local, Modular

A lightweight, high-performance image processing toolkit built with Streamlit.

Designed for real-world workflows — resizing, compression, conversion, and merging — all done locally without uploading files to external servers.

---

## ⚡ Features

### 📦 Image Resizer & Compressor

* Target file size compression (binary search based)
* DPI and quality control
* Format conversion (JPEG, PNG, WebP)
* Smart compression (avoids increasing size)

---

### 📄 Image → PDF

* Convert multiple images into a single PDF
* Automatic format handling
* Optimized output

---

### 🧩 Image Merger

* Combine multiple images into one
* Vertical / horizontal merging
* Resolution-aware processing

---

### 📚 PDF Merger

* Merge multiple PDFs into a single file
* Fast and lossless

---

## 🧠 Design Principles

* 🔒 Local-first (no external uploads)
* ⚡ Fast startup (minimal dependencies)
* 🧩 Modular architecture (separate tools)
* 🛡️ Safe processing (validation + fallback)

---

## 📦 Installation

```bash
git clone https://github.com/dipenduadhikari13-byte/Image-Tools.git
cd Image-Tools
pip install -r requirements.txt
```

---

## ▶️ Run

```bash
streamlit run app.py
```

---

## ☁️ Deployment (Streamlit Cloud)

Includes:

* `requirements.txt` → Python dependencies
* `packages.txt` → system dependencies (qpdf)

Works directly on Streamlit Community Cloud.

---

## 📁 Project Structure

```text
app.py
pages/
 ├── image_resizer.py
 ├── image_to_pdf.py
 ├── image_merger.py
 ├── pdf_merger.py

utils/
 └── image_utils.py
```

---

## ⚠️ Notes

* Large images may consume high memory
* Compression effectiveness depends on image content
* PDF merging is lossless (no quality reduction)

---

## 🚀 Future Improvements

* Batch processing (folder input)
* Drag & drop multi-file support
* Background removal (separate AI module)
* CLI version

---

## 📜 License

MIT License
