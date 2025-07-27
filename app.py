import streamlit as st
from streamlit_drawable_canvas import st_canvas
import pandas as pd
import numpy as np
import sqlite3
from datetime import time, timedelta, datetime
from fpdf import FPDF
import io
import base64

# ---------------------- CONFIGURATIONS ----------------------
st.set_page_config(page_title="Retort F0 Tools - Rumah Retort Bersama", layout="wide")

DB_PATH = "retort_data.db"

# ---------------------- DATABASE INIT ----------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS hasil_f0 (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        waktu TEXT,
                        suhu REAL,
                        tekanan REAL,
                        keterangan TEXT
                    )''')
    conn.commit()
    conn.close()

init_db()

# ---------------------- PAGE SETUP ----------------------
st.sidebar.title("📋 Navigasi")
page = st.sidebar.radio("Pilih halaman:", ["🏠 Dashboard", "🧪 Input Data", "📈 Hasil F0"])

# ---------------------- SESSION STATE SETUP ----------------------
if 'user' not in st.session_state:
    st.session_state.user = None

# ---------------------- LOGIN ----------------------
def login_page():
    st.title("🔐 Login")
    username = st.text_input("Masukkan nama pengguna")
    if st.button("Login"):
        if username.lower() in ["bagoes", "iwan", "dimas"]:
            st.session_state.user = username
            st.success(f"Selamat datang, {username}!")
        else:
            st.error("Nama pengguna tidak dikenal.")

if st.session_state.user is None:
    login_page()
    st.stop()

# ---------------------- DASHBOARD ----------------------
def dashboard_page():
    st.title("🏠 Dashboard Retort Tools")
    st.markdown("""
    ### Selamat datang di aplikasi Tools Proses Retort F0
    Aplikasi ini membantu mencatat data proses retort, menghitung nilai F0, dan mengunduh laporan PDF.
    
    **Pengguna terautentikasi:** {user}
    """.format(user=st.session_state.user))

# ---------------------- INPUT DATA ----------------------
def input_data_page():
    st.title("🧪 Input Data Proses Retort")
    # Input waktu
    waktu = st.time_input("Waktu", value=time(0, 0))

# Validasi waktu maksimal 2 jam
if datetime.combine(datetime.today(), waktu) - datetime.combine(datetime.today(), time(0, 0)) > timedelta(hours=2):
    st.error("Waktu tidak boleh lebih dari 2 jam (120 menit). Silakan masukkan ulang.")
else:
    # Lanjutkan proses jika valid
    # Misal:
    suhu = st.number_input("Suhu (°C)", min_value=0.0)
    tekanan = st.number_input("Tekanan (psi/bar)", min_value=0.0)
    keterangan = st.text_input("Keterangan (Opsional)")
    suhu = st.number_input("Suhu (°C)", min_value=0.0)
    tekanan = st.number_input("Tekanan (bar)", min_value=0.0)
    keterangan = st.text_input("Keterangan")

    if st.button("Simpan Data"):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO hasil_f0 (waktu, suhu, tekanan, keterangan) VALUES (?, ?, ?, ?)",
                       (waktu.strftime('%H:%M:%S'), suhu, tekanan, keterangan))
        conn.commit()
        conn.close()
        st.success("✅ Data berhasil disimpan!")

    st.markdown("---")
    st.subheader("📋 Data Tersimpan")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM hasil_f0", conn)
    conn.close()
    st.dataframe(df)

# ---------------------- HITUNG F0 ----------------------
def calculate_f0(df):
    df['F0'] = 0.0
    T_ref = 121.1
    z = 10
    dt = 1  # Asumsi tiap data 1 menit

    for i in range(len(df)):
        if df.loc[i, 'suhu'] > 90:
            f0 = 10 ** ((df.loc[i, 'suhu'] - T_ref) / z)
            df.loc[i, 'F0'] = f0 * dt

    total_f0 = df['F0'].sum()
    return df, total_f0

# ---------------------- EXPORT PDF ----------------------
def export_pdf(df, total_f0, jumlah_awal_produk, jumlah_akhir_produk, basket_1, basket_2, basket_3):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, "LAPORAN PROSES RETORT", ln=1, align="C")
    pdf.cell(0, 10, "", ln=1)

    pdf.cell(0, 10, f"Total Nilai F0: {total_f0:.2f}", ln=1)
    pdf.cell(0, 10, f"Jumlah Produk Awal       : {jumlah_awal_produk}", ln=1)
    pdf.cell(0, 10, f"Jumlah Produk Akhir      : {jumlah_akhir_produk}", ln=1)
    pdf.cell(0, 10, f"Distribusi Basket:", ln=1)
    pdf.cell(0, 10, f"  - Basket 1             : {basket_1}", ln=1)
    pdf.cell(0, 10, f"  - Basket 2             : {basket_2}", ln=1)
    pdf.cell(0, 10, f"  - Basket 3             : {basket_3}", ln=1)
    pdf.cell(0, 10, f"", ln=1)

    for i, row in df.iterrows():
        pdf.cell(0, 10, f"{row['waktu']} | Suhu: {row['suhu']}°C | Tekanan: {row['tekanan']} bar | F0: {row['F0']:.2f} | {row['keterangan']}", ln=1)

    pdf.cell(0, 10, "", ln=1)
    pdf.set_font("Arial", style="I", size=10)
    pdf.multi_cell(0, 10, "Proses Retort Dilakukan Oleh Rumah Retort Bersama", align="C")

    return pdf.output(dest='S').encode('latin1')

# ---------------------- HASIL F0 ----------------------
def hasil_f0_page():
    st.title("📈 Hasil Perhitungan F0")

    st.subheader("📦 Distribusi Produk ke Basket")
    col1, col2 = st.columns(2)
    with col1:
        jumlah_awal_produk = st.number_input("Jumlah Produk Awal", min_value=0, step=1, key="jumlah_awal_produk")
    with col2:
        jumlah_akhir_produk = st.number_input("Jumlah Produk Akhir (Setelah Retort)", min_value=0, step=1, key="jumlah_akhir_produk")

    basket_1 = st.number_input("Jumlah di Basket 1", min_value=0, step=1, key="basket_1")
    basket_2 = st.number_input("Jumlah di Basket 2", min_value=0, step=1, key="basket_2")
    basket_3 = st.number_input("Jumlah di Basket 3", min_value=0, step=1, key="basket_3")

    if jumlah_awal_produk != basket_1 + basket_2 + basket_3:
        st.warning("⚠️ Jumlah produk di basket tidak sama dengan jumlah awal.")

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM hasil_f0", conn)
    conn.close()

    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    if st.button("🔍 Hitung F0"):
        df_hasil, total_f0 = calculate_f0(edited_df)
        st.success(f"Total Nilai F0: {total_f0:.2f}")
        st.dataframe(df_hasil)

        # PDF Export
        pdf_bytes = export_pdf(df_hasil, total_f0, jumlah_awal_produk, jumlah_akhir_produk, basket_1, basket_2, basket_3)
        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="laporan_f0.pdf">📄 Unduh PDF</a>'
        st.markdown(href, unsafe_allow_html=True)

# ---------------------- ROUTING ----------------------
if page == "🏠 Dashboard":
    dashboard_page()
elif page == "🧪 Input Data":
    input_data_page()
elif page == "📈 Hasil F0":
    hasil_f0_page()
