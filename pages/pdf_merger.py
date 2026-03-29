import io

import streamlit as st

from utils.image_utils import format_size, merge_pdfs


st.set_page_config(page_title="PDF Merger", page_icon="📚", layout="wide")

st.title("📚 Merge PDFs")
st.caption("Upload 2-8 PDF files and combine them into a single PDF.")

pdf_merge_files = st.file_uploader(
    "Upload 2-8 PDF files to merge",
    type=["pdf"],
    accept_multiple_files=True,
    key="merge_pdf_upload",
)

if pdf_merge_files:
    if len(pdf_merge_files) < 2:
        st.warning("⚠️ Please upload at least 2 PDFs to merge.")
    elif len(pdf_merge_files) > 8:
        st.warning("⚠️ Maximum 8 PDFs. Using the first 8.")
        pdf_merge_files = pdf_merge_files[:8]

    if len(pdf_merge_files) >= 2:
        st.success(f"✅ {len(pdf_merge_files)} PDFs ready to merge")

        total_input_size = 0
        for idx, f in enumerate(pdf_merge_files):
            fsize = len(f.getvalue())
            total_input_size += fsize
            st.write(f"**{idx + 1}.** {f.name} — {format_size(fsize)}")

        st.caption(f"📊 Total input size: **{format_size(total_input_size)}**")

        if st.button("📚 Merge PDFs", type="primary", key="merge_pdf_btn"):
            with st.spinner("Merging PDFs..."):
                try:
                    pdf_buffers = [io.BytesIO(f.getvalue()) for f in pdf_merge_files]
                    merged_pdf_bytes, total_pages = merge_pdfs(pdf_buffers)
                    merged_pdf_size = len(merged_pdf_bytes)
                except ImportError:
                    st.error("❌ `pypdf` is required for PDF merging. Install it: `pip install pypdf`")
                    st.stop()
                except Exception as e:
                    st.error(f"❌ Failed to merge PDFs: {e}")
                    st.stop()

            st.markdown("---")
            st.success(f"✅ Merged! — **{total_pages} pages** — **{format_size(merged_pdf_size)}**")

            c1, c2, c3 = st.columns(3)
            c1.metric("Files Merged", len(pdf_merge_files))
            c2.metric("Total Pages", total_pages)
            c3.metric("Output Size", format_size(merged_pdf_size))

            st.download_button(
                label=f"⬇️ Download Merged PDF ({format_size(merged_pdf_size)})",
                data=merged_pdf_bytes,
                file_name="merged_document.pdf",
                mime="application/pdf",
                type="primary",
                key="dl_merge_pdf_btn",
            )
else:
    st.info("👆 Upload 2-8 PDF files to merge them into one full pdf.")
