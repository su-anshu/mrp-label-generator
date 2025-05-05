import streamlit as st
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib.utils import ImageReader
from io import BytesIO
from datetime import datetime
from dateutil.relativedelta import relativedelta
import random
import os
import fitz  # PyMuPDF
from PIL import Image
import re

# Constants
LABEL_WIDTH = 48 * mm
LABEL_HEIGHT = 25 * mm
DATA_PATH = "data/latest_data.xlsx"
BARCODE_PDF_PATH = "data/master_fnsku.pdf"
BACKUP_DIR = "data/backups"

# Ensure directories exist
os.makedirs("data", exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

def sanitize_filename(name):
    return re.sub(r'\W+', '_', name)

def load_data():
    return pd.read_excel(DATA_PATH)

def backup_file(original_path, prefix):
    if os.path.exists(original_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(original_path)[-1]
        backup_filename = f"{prefix}_{timestamp}{ext}"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        with open(original_path, "rb") as src, open(backup_path, "wb") as dst:
            dst.write(src.read())
        return backup_path
    return None

def clear_files():
    deleted = []
    for path in [DATA_PATH, BARCODE_PDF_PATH]:
        if os.path.exists(path):
            os.remove(path)
            deleted.append(path)
    return deleted

def generate_pdf(dataframe):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    today = datetime.today()
    mfg_date = today.strftime('%d %b %Y').upper()
    use_by = (today + relativedelta(months=6)).strftime('%d %b %Y').upper()
    date_code = today.strftime('%d%m%y')

    for _, row in dataframe.iterrows():
        name = str(row['Name'])
        weight = str(row['Net Weight'])
        try:
            mrp = f"INR {int(float(row['M.R.P']))}"
        except:
            mrp = "INR N/A"

        try:
            fssai = str(int(float(row['M.F.G. FSSAI'])))
        except:
            fssai = "N/A"

        product_prefix = ''.join(filter(str.isalnum, name.upper()))[:2]
        batch_code = f"{product_prefix}{date_code}{str(random.randint(1, 999)).zfill(3)}"

        c.setFont("Helvetica-Bold", 6)
        c.drawString(2 * mm, 22 * mm, f"Name: {name}")
        c.drawString(2 * mm, 18 * mm, f"Net Weight: {weight} Kg")
        c.drawString(2 * mm, 14 * mm, f"M.R.P: {mrp}")
        c.drawString(2 * mm, 10 * mm, f"M.F.G: {mfg_date} | USE BY: {use_by}")
        c.drawString(2 * mm, 6 * mm, f"Batch Code: {batch_code}")
        c.drawString(2 * mm, 2 * mm, f"M.F.G. FSSAI: {fssai}")
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer

def extract_fnsku_page(fnsku_code, pdf_path):
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            if fnsku_code in page.get_text():
                single_page_pdf = fitz.open()
                single_page_pdf.insert_pdf(doc, from_page=i, to_page=i)
                buffer = BytesIO()
                single_page_pdf.save(buffer)
                buffer.seek(0)
                return buffer
    except Exception as e:
        print("Error extracting FNSKU:", e)
    return None

def generate_combined_label_pdf(mrp_df, fnsku_code, barcode_pdf_path):
    buffer = BytesIO()
    mrp_label_buffer = generate_pdf(mrp_df)

    try:
        doc = fitz.open(barcode_pdf_path)
        for page in doc:
            if fnsku_code in page.get_text():
                barcode_pix = page.get_pixmap(dpi=300)
                break
        else:
            return None
    except Exception as e:
        print("Error reading barcode PDF:", e)
        return None

    try:
        mrp_pdf = fitz.open(stream=mrp_label_buffer.read(), filetype="pdf")
        mrp_pix = mrp_pdf[0].get_pixmap(dpi=300)
        mrp_img = Image.open(BytesIO(mrp_pix.tobytes("png")))
        barcode_img = Image.open(BytesIO(barcode_pix.tobytes("png")))
    except Exception as e:
        print("Error converting PDFs to images:", e)
        return None

    c = canvas.Canvas(buffer, pagesize=(96 * mm, 25 * mm))
    c.drawImage(ImageReader(mrp_img), 0, 0, width=48 * mm, height=25 * mm)
    c.drawImage(ImageReader(barcode_img), 48 * mm, 0, width=48 * mm, height=25 * mm)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ----------------------------- UI -----------------------------

st.set_page_config(page_title="MRP Label Generator", layout="centered")
st.title("📦 MRP Label Generator")
mode = st.sidebar.radio("Select Mode", ["User", "Admin 👑"])

# ----------------------------- Admin -----------------------------

if mode == "Admin 👑":
    st.subheader("🔐 Admin Login")
    admin_pass = st.text_input("Enter Admin Password", type="password")
    if admin_pass == "admin@2025#":
        st.success("Welcome, Admin!")

        st.markdown("### 📁 Current Files in Use")

        if os.path.exists(DATA_PATH):
            ts = datetime.fromtimestamp(os.path.getmtime(DATA_PATH)).strftime('%d %b %Y, %I:%M %p')
            st.success(f"🟢 MRP Excel: `{DATA_PATH}` (Last Updated: {ts})")
            with open(DATA_PATH, "rb") as f:
                st.download_button("📥 Download Current MRP Excel", f, file_name="latest_data.xlsx")
        else:
            st.error("🔴 MRP Excel file not found.")

        if os.path.exists(BARCODE_PDF_PATH):
            ts = datetime.fromtimestamp(os.path.getmtime(BARCODE_PDF_PATH)).strftime('%d %b %Y, %I:%M %p')
            st.success(f"🟢 Barcode PDF: `{BARCODE_PDF_PATH}` (Last Updated: {ts})")
            with open(BARCODE_PDF_PATH, "rb") as f:
                st.download_button("📥 Download Current Barcode PDF", f, file_name="master_fnsku.pdf")
        else:
            st.error("🔴 Barcode PDF file not found.")

        if st.button("🧹 Clear Both Files (MRP + Barcode)"):
            deleted = clear_files()
            if deleted:
                st.success(f"✅ Deleted: {', '.join(deleted)}")
            else:
                st.info("ℹ️ Nothing to delete.")

        st.markdown("---")
        st.subheader("⬆️ Upload New Files")

        uploaded_file = st.file_uploader("Upload New Excel Data (.xlsx)", type=["xlsx"])
        if uploaded_file:
            try:
                backup_file(DATA_PATH, "excel")
                df = pd.read_excel(uploaded_file)
                df.to_excel(DATA_PATH, index=False)
                st.success("✅ Excel uploaded and backed up!")
            except Exception as e:
                st.error(f"❌ Excel upload failed: {e}")

        barcode_pdf = st.file_uploader("Upload Master Barcode PDF", type=["pdf"])
        if barcode_pdf:
            try:
                backup_file(BARCODE_PDF_PATH, "barcode")
                with open(BARCODE_PDF_PATH, "wb") as f:
                    f.write(barcode_pdf.read())
                st.success("✅ Barcode PDF uploaded and backed up!")
            except Exception as e:
                st.error(f"❌ Barcode upload failed: {e}")
    else:
        st.warning("Enter the correct password to access admin panel.")

# ----------------------------- User -----------------------------

else:
    st.caption("Generate 48mm x 25mm labels with pricing, batch code, dates, and barcode.")

    if os.path.exists(DATA_PATH):
        try:
            df = load_data()

            st.subheader("🎯 Select Product & Weight")
            product_options = sorted(df['Name'].dropna().unique())
            selected_product = st.selectbox("Product", product_options)
            product_weights = sorted(df[df['Name'] == selected_product]['Net Weight'].dropna().unique())
            selected_weight = st.selectbox("Net Weight", product_weights)

            safe_name = sanitize_filename(selected_product)
            filtered_df = df[(df['Name'] == selected_product) & (df['Net Weight'] == selected_weight)]

            with st.expander("🔍 Preview Filtered Data"):
                st.dataframe(filtered_df)

            if not filtered_df.empty:
                if st.button("📥 Download MRP Label PDF"):
                    pdf = generate_pdf(filtered_df)
                    st.download_button("⬇️ Download Label", data=pdf, file_name=f"{safe_name}_Label.pdf", mime="application/pdf")

                if 'FNSKU' in filtered_df.columns and os.path.exists(BARCODE_PDF_PATH):
                    fnsku_code = str(filtered_df.iloc[0]['FNSKU']).strip()
                    barcode = extract_fnsku_page(fnsku_code, BARCODE_PDF_PATH)
                    if barcode:
                        st.download_button("📦 Download Barcode", data=barcode, file_name=f"{fnsku_code}_barcode.pdf", mime="application/pdf")

                        combined = generate_combined_label_pdf(filtered_df, fnsku_code, BARCODE_PDF_PATH)
                        if combined:
                            st.download_button("🧾 Download Combined Label", data=combined, file_name=f"{safe_name}_Combined.pdf", mime="application/pdf")
                        else:
                            st.info("ℹ️ Could not generate combined label.")
                    else:
                        st.warning("⚠️ FNSKU not found in barcode PDF.")
                else:
                    st.info("ℹ️ FNSKU missing or barcode PDF not uploaded.")
            else:
                st.warning("⚠️ No matching data found.")
        except Exception as e:
            st.error(f"❌ Error: {e}")
    else:
        st.warning("⚠️ No product data found. Ask admin to upload.")
