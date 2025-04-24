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

# Constants
LABEL_WIDTH = 48 * mm
LABEL_HEIGHT = 25 * mm
DATA_PATH = "data/latest_data.xlsx"
BARCODE_PDF_PATH = "data/master_fnsku.pdf"

os.makedirs("data", exist_ok=True)

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
        random_suffix = str(random.randint(1, 999)).zfill(3)
        batch_code = f"{product_prefix}{date_code}{random_suffix}"

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
            text = page.get_text()
            if fnsku_code in text:
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
        barcode_pix = None
        for i, page in enumerate(doc):
            if fnsku_code in page.get_text():
                barcode_pix = page.get_pixmap(dpi=300)
                break
    except Exception as e:
        print("Error reading barcode PDF:", e)
        return None

    if not barcode_pix:
        return None

    try:
        mrp_pdf = fitz.open(stream=mrp_label_buffer.read(), filetype="pdf")
        mrp_pix = mrp_pdf[0].get_pixmap(dpi=300)
        mrp_img = Image.open(BytesIO(mrp_pix.tobytes("png")))
    except Exception as e:
        print("Error converting MRP PDF to image:", e)
        return None

    barcode_img = Image.open(BytesIO(barcode_pix.tobytes("png")))
    c = canvas.Canvas(buffer, pagesize=(96 * mm, 25 * mm))
    c.drawImage(ImageReader(mrp_img), 0, 0, width=48 * mm, height=25 * mm)
    c.drawImage(ImageReader(barcode_img), 48 * mm, 0, width=48 * mm, height=25 * mm)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="MRP Label Generator", layout="centered")
st.title("📦 MRP Label Generator")

mode = st.sidebar.radio("Select Mode", ["User", "Admin 👑"])

# -----------------------------
# Admin Mode
# -----------------------------
if mode == "Admin 👑":
    st.subheader("🔐 Admin Login")
    admin_pass = st.text_input("Enter Admin Password", type="password")

    if admin_pass == "admin@2025#":
        st.success("Welcome, Admin!")

        uploaded_file = st.file_uploader("Upload New Excel Data (.xlsx)", type=["xlsx"])
        if uploaded_file:
            try:
                if os.path.exists(DATA_PATH):
                    os.remove(DATA_PATH)  # ✅ Delete old file before saving
                df = pd.read_excel(uploaded_file)
                df.to_excel(DATA_PATH, index=False)
                st.success(f"✅ File uploaded and saved at `{DATA_PATH}`")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving file: {e}")

        barcode_pdf = st.file_uploader("Upload Master Barcode PDF", type=["pdf"])
        if barcode_pdf:
            try:
                with open(BARCODE_PDF_PATH, "wb") as f:
                    f.write(barcode_pdf.read())
                st.success("✅ Barcode PDF uploaded!")
            except Exception as e:
                st.error(f"Error saving barcode PDF: {e}")
    else:
        st.warning("Enter the correct password to access admin panel.")

# -----------------------------
# User Mode
# -----------------------------
else:
    st.caption("Generate high-quality 48mm x 25mm product labels with batch codes, dates, and pricing.")
    st.markdown("---")

    if os.path.exists(DATA_PATH):
        try:
            df = pd.read_excel(DATA_PATH)
            if not {'Name', 'Net Weight'}.issubset(df.columns):
                st.error("Missing required columns in Excel file: 'Name', 'Net Weight'")
            else:
                df = df.dropna(subset=['Name', 'Net Weight'])

                if st.button("🔄 Refresh Product List"):
                    st.rerun()

                st.subheader("🎯 Select Product & Weight")
                product_options = sorted(df['Name'].dropna().unique())
                selected_product = st.selectbox("Select Product", product_options)

                product_weights = sorted(df[df['Name'] == selected_product]['Net Weight'].dropna().unique())
                selected_weight = st.selectbox("Select Net Weight", product_weights)

                filtered_df = df[(df['Name'] == selected_product) & (df['Net Weight'] == selected_weight)]

                with st.expander("🔍 Preview Filtered Data"):
                    st.dataframe(filtered_df)

                st.markdown("---")
                st.subheader("🖨️ Generate Label")

                if not filtered_df.empty:
                    if st.button("📥 Download Label PDF"):
                        pdf_buffer = generate_pdf(filtered_df)
                        st.download_button(
                            label="⬇️ Click to Download PDF",
                            data=pdf_buffer,
                            file_name=f"{selected_product}_{selected_weight}_Labels.pdf",
                            mime="application/pdf"
                        )

                    if 'FNSKU' in filtered_df.columns and os.path.exists(BARCODE_PDF_PATH):
                        fnsku_code = str(filtered_df.iloc[0]['FNSKU']).strip()
                        barcode_pdf = extract_fnsku_page(fnsku_code, BARCODE_PDF_PATH)

                        if barcode_pdf:
                            st.download_button(
                                label="📦 Download Matching Barcode Label",
                                data=barcode_pdf,
                                file_name=f"{fnsku_code}_barcode.pdf",
                                mime="application/pdf"
                            )

                            combined_pdf = generate_combined_label_pdf(filtered_df, fnsku_code, BARCODE_PDF_PATH)
                            if combined_pdf:
                                st.download_button(
                                    label="🧾 Download Combined MRP + Barcode Label",
                                    data=combined_pdf,
                                    file_name=f"{selected_product}_{selected_weight}_Combined.pdf",
                                    mime="application/pdf"
                                )
                            else:
                                st.info("ℹ️ Could not generate combined label.")
                        else:
                            st.info("ℹ️ No matching barcode found in uploaded PDF.")
                    else:
                        st.info("ℹ️ FNSKU not available or barcode PDF not uploaded.")
                else:
                    st.warning("⚠️ No matching data found for the selected product and weight.")
        except Exception as e:
            st.error(f"❌ Error loading saved data: {e}")
    else:
        st.warning("⚠️ No product data found. Please contact admin to upload.")
