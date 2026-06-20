"""GST Invoice Signing Tool — Streamlit desktop application."""

from __future__ import annotations

import streamlit as st

from gst_signer.processor import (
    OWNER_LINE,
    create_zip,
    process_cams_pdf,
    process_kfin_pdf,
)

st.set_page_config(
    page_title="GST Invoice Signing Tool",
    page_icon="📄",
    layout="centered",
)

st.title("GST Invoice Signing Tool")
st.markdown(f"**Owner:** {OWNER_LINE}")
st.markdown(
    "Upload CAMS and KFintech invoice files plus your signature image. "
    "Both CAMS and KFintech accept a combined PDF or a ZIP/RAR bundle with "
    "nested archives per company (each containing the invoice PDF). "
    "Output: one ZIP containing cams_signed.zip, kfin_signed.zip, and signed_files.txt."
)

cams_file = st.file_uploader(
    "Upload CAMS PDF / ZIP / RAR",
    type=["pdf", "zip", "rar"],
    key="cams_pdf",
    help=(
        "Upload the combined CAMS file: a single PDF or a ZIP/RAR bundle with "
        "one nested archive per company, each containing the invoice PDF."
    ),
)
kfin_file = st.file_uploader(
    "Upload KFintech PDF / ZIP / RAR",
    type=["pdf", "zip", "rar"],
    key="kfin_pdf",
    help=(
        "Upload the combined KFintech file. New format: a ZIP/RAR bundle with "
        "one nested archive per company, each containing the invoice PDF."
    ),
)
signature_file = st.file_uploader("Upload Signature PNG", type=["png"], key="signature_png")
signatory_name = st.text_input(
    "Signatory Name (for KFintech invoices)",
    placeholder="e.g. Narendra Kumar Arya",
    help="This name is placed above 'Name of the Signatory' on KFintech invoices.",
)

logs: list[str] = []
progress_bar = st.progress(0)
log_container = st.empty()

generate = st.button("Generate Signed Invoices", type="primary", use_container_width=True)


def append_log(message: str) -> None:
    logs.append(message)
    log_container.code("\n".join(logs), language="text")


if generate:
    if cams_file is None and kfin_file is None:
        st.error("Please upload at least one file (CAMS or KFintech PDF/ZIP/RAR).")
    elif signature_file is None:
        st.error("Please upload a signature PNG image.")
    elif kfin_file is not None and not signatory_name.strip():
        st.error("Please enter the signatory name for KFintech invoices.")
    else:
        try:
            signature_bytes = signature_file.read()
            cams_signed: dict[str, bytes] = {}
            kfin_signed: dict[str, bytes] = {}
            cams_names: list[str] = []
            kfin_names: list[str] = []

            total_steps = int(bool(cams_file)) + int(bool(kfin_file)) + 1
            step = 0

            if cams_file:
                append_log("Processing CAMS file...")
                progress_bar.progress(step / total_steps)
                cams_signed = process_cams_pdf(cams_file.read(), signature_bytes, append_log)
                cams_names = sorted(cams_signed.keys())
                step += 1
                progress_bar.progress(step / total_steps)

            if kfin_file:
                append_log("Processing KFintech file...")
                progress_bar.progress(step / total_steps)
                kfin_signed = process_kfin_pdf(
                    kfin_file.read(),
                    signature_bytes,
                    append_log,
                    signatory_name=signatory_name.strip(),
                )
                kfin_names = sorted(kfin_signed.keys())
                step += 1
                progress_bar.progress(step / total_steps)

            total_signed = len(cams_signed) + len(kfin_signed)
            if total_signed == 0:
                st.error("No invoices were processed. Check that the PDFs contain valid invoice pages.")
            else:
                append_log("Creating ZIP archive...")
                zip_bytes = create_zip(
                    cams_files=cams_signed,
                    kfin_files=kfin_signed,
                    cams_names=cams_names,
                    kfin_names=kfin_names,
                )
                append_log("ZIP Created Successfully")
                progress_bar.progress(1.0)

                st.success(
                    f"Successfully signed {total_signed} invoice(s). "
                    "Download the ZIP file below."
                )

                st.download_button(
                    label="Download signed_invoices.zip",
                    data=zip_bytes,
                    file_name="signed_invoices.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

        except ValueError as exc:
            st.error(f"Processing error: {exc}")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")

st.divider()
st.caption(f"© {OWNER_LINE} — GST Invoice Signing Tool")
