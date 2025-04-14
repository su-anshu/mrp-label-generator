import streamlit as st
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from io import BytesIO
from datetime import datetime
from dateutil.relativedelta import relativedelta
import random

# Constants
LABEL_WIDTH = 48 * mm
LABEL_HEIGHT = 25 * mm

def generate_pdf(dataframe):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    today = datetime.today()
    mfg_date = today.strftime('%d %b %Y').upper()
    use_by = (today + relativedelta(months=6)).strftime('%d %b %Y').upper()
    date_code = today.strftime('%d%m%y')  # e.g., 140425

    for _, row in dataframe.iterrows():
        # Format fields
        name = str(row['Name'])
        weight = str(row['Net Weight'])
        mrp = f"INR {int(float(row['M.R.P']))}"

        # Handle missing FSSAI
        try:
            fssai = str(int(float(row['M.F.G. FSAAI'])))
        except:
            fssai = "N/A"

        # Generate batch code dynamically using first 2 letters of product name
        product_prefix = ''.join(filter(str.isalnum, name.upper()))[:2]
        random_suffix = str(random.randint(1, 999)).zfill(3)
        batch_code = f"{product_prefix}{date_code}{random_suffix}"

        # Draw on label
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

# -----------------------------
# Streamlit UI
# -----------------------------

st.set_page_config(page_title="MRP Label Generator", layout="centered")

st.title("📦 MRP Label Generator")
st.caption("Generate high-quality 48mm x 25mm product labels with batch codes, dates, and pricing.")

st.markdown("---")
st.subheader("🗂 Upload Your Product Excel File")

uploaded_file = st.file_uploader("Choose an Excel file (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ File uploaded and loaded successfully!")

        st.markdown("---")
        st.subheader("🎯 Select Product & Weight")

        # Select Product
        product_options = sorted(df['Name'].dropna().unique())
        selected_product = st.selectbox("Select Product", product_options)

        # Filter weights dynamically based on selected product
        product_weights = sorted(df[df['Name'] == selected_product]['Net Weight'].dropna().unique())
        selected_weight = st.selectbox("Select Net Weight", product_weights)

        # Filter data
        filtered_df = df[(df['Name'] == selected_product) & (df['Net Weight'] == selected_weight)]

        with st.expander("🔍 Preview Filtered Data"):
            st.dataframe(filtered_df)

        st.markdown("---")
        st.subheader("🖨️ Generate Label")

        if not filtered_df.empty and st.button("📥 Download Label PDF"):
            pdf_buffer = generate_pdf(filtered_df)
            st.download_button(
                label="⬇️ Click to Download PDF",
                data=pdf_buffer,
                file_name=f"{selected_product}_{selected_weight}_Labels.pdf",
                mime="application/pdf"
            )
        elif filtered_df.empty:
            st.warning("⚠️ No matching data found for the selected product and weight.")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
else:
    st.info("📤 Please upload an Excel file to get started.")
