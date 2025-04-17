import streamlit as st
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from io import BytesIO
from datetime import datetime
from dateutil.relativedelta import relativedelta
import random
import os

# Constants
LABEL_WIDTH = 48 * mm
LABEL_HEIGHT = 25 * mm
DATA_PATH = "data/latest_data.xlsx"  # Save uploaded file here

# Create data directory if doesn't exist
os.makedirs("data", exist_ok=True)

def generate_pdf(dataframe):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))

    today = datetime.today()
    mfg_date = today.strftime('%d %b %Y').upper()
    use_by = (today + relativedelta(months=6)).strftime('%d %b %Y').upper()
    date_code = today.strftime('%d%m%y')  # e.g., 140425

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

    if admin_pass == "admin@2025#":  # <-- change this to a secure password
        st.success("Welcome, Admin!")
        uploaded_file = st.file_uploader("Upload New Excel Data (.xlsx)", type=["xlsx"])
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                df.to_excel(DATA_PATH, index=False)
                st.success("✅ File uploaded and saved for users!")
            except Exception as e:
                st.error(f"Error saving file: {e}")
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
            st.error(f"❌ Error loading saved data: {e}")
    else:
        st.warning("⚠️ No product data found. Please contact admin to upload.")
