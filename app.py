import streamlit as st
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from io import BytesIO
from datetime import datetime
from dateutil.relativedelta import relativedelta
import random
import os
import tempfile
import platform

# Constants
LABEL_WIDTH = 48 * mm
LABEL_HEIGHT = 25 * mm

# Generate PDF label
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
        mrp = f"INR {int(float(row['M.R.P']))}"

        try:
            fssai = str(int(float(row['M.F.G. FSAAI'])))
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

# Print PDF locally
def print_pdf_locally(pdf_data: BytesIO):
    system = platform.system()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(pdf_data.read())
    tmp.close()

    if system == "Windows":
        import win32print
        import win32api
        printer_name = win32print.GetDefaultPrinter()
        win32api.ShellExecute(
            0,
            "print",
            tmp.name,
            f'/d:"{printer_name}"',
            ".",
            0
        )
    elif system in ["Linux", "Darwin"]:
        os.system(f"lp {tmp.name}")
    else:
        st.error("🚫 Printing not supported on this OS.")

# -----------------------------
# Streamlit UI
# -----------------------------

st.set_page_config(page_title="MRP Label Generator", layout="centered")

st.title("📦 MRP Label Generator")
st.caption("Generate and print high-quality 48mm x 25mm product labels.")

st.markdown("---")
st.subheader("🗂 Upload Product Excel File")

uploaded_file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ File loaded successfully!")

        st.markdown("---")
        st.subheader("🎯 Select Product Details")

        product_options = sorted(df['Name'].dropna().unique())
        selected_product = st.selectbox("Select Product", product_options)

        product_weights = sorted(df[df['Name'] == selected_product]['Net Weight'].dropna().unique())
        selected_weight = st.selectbox("Select Net Weight", product_weights)

        filtered_df = df[(df['Name'] == selected_product) & (df['Net Weight'] == selected_weight)]

        with st.expander("🔍 Preview Filtered Data"):
            st.dataframe(filtered_df)

        st.markdown("---")
        st.subheader("🖨️ Generate & Print")

        if not filtered_df.empty:
            pdf_buffer = generate_pdf(filtered_df)

            col1, col2 = st.columns(2)

            with col1:
                st.download_button(
                    label="⬇️ Download Label PDF",
                    data=pdf_buffer,
                    file_name=f"{selected_product}_{selected_weight}_Labels.pdf",
                    mime="application/pdf"
                )

            with col2:
                if st.button("🖨️ Print Now"):
                    try:
                        print_pdf_locally(BytesIO(pdf_buffer.read()))
                        st.success("🖨️ Sent to printer successfully!")
                    except Exception as e:
                        st.error(f"⚠️ Printing failed: {e}")
        else:
            st.warning("⚠️ No matching data found.")
    except Exception as e:
        st.error(f"❌ Error: {e}")
else:
    st.info("📤 Please upload your Excel file to begin.")
