import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import io
import datetime
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import sqlite3
import os

# ----------------------------
# KONFIGURASI
# ----------------------------
DB_PATH = "data_retort.db"
F0_REFERENCE_TEMP = 121.1
Z_VALUE = 10
AUTHORIZED_USERS = ["bagoes", "dimas", "iwan"]

# ----------------------------
# HALAMAN LOGIN
# ----------------------------
def show_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.image(LOGO_PATH, width=200)
        st.title("Login Aplikasi Proses Retort R2B")
        username = st.text_input("Masukkan Nama (bagoes / dimas / iwan)")

        if st.button("Login"):
            if username.strip().lower() in AUTHORIZED_USERS:
                st.session_state.logged_in = True
                st.success(f"Selamat datang, {username.capitalize()}! Anda berhasil login.")
                st.experimental_rerun()
            else:
                st.error("Nama tidak dikenal. Silakan coba lagi.")
        return False
    return True

if not show_login():
    st.stop()


# ----------------------------
# INISIALISASI DATABASE
# ----------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS pelanggan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT, tanggal TEXT, sesi TEXT, batch TEXT,
            total_waktu INTEGER, jenis_produk TEXT,
            jumlah_awal INTEGER, jumlah_akhir INTEGER,
            basket1 INTEGER, basket2 INTEGER, basket3 INTEGER,
            petugas TEXT, paraf TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS f0_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pelanggan_id INTEGER,
            menit INTEGER, suhu REAL, tekanan REAL, keterangan TEXT,
            f0 REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ----------------------------
# Fungsi hitung F₀
# ----------------------------
def calculate_f0(temps, T_ref=F0_REFERENCE_TEMP, z=Z_VALUE):
    f0_values = []
    for T in temps:
        if T < 90:
            f0_values.append(0)
        else:
            f0_values.append(10 ** ((T - T_ref) / z))
    return np.cumsum(f0_values)

# Fungsi cek suhu minimal 121.1°C selama ≥3 menit
def check_minimum_holding_time(temps, min_temp=F0_REFERENCE_TEMP, min_duration=3):
    holding_minutes = 0
    for t in temps:
        if t >= min_temp:
            holding_minutes += 1
        else:
            holding_minutes = 0
        if holding_minutes >= min_duration:
            return True
    return False

# ----------------------------
# HALAMAN HASIL F0
# ----------------------------
def hasil_f0_page():
    st.title("📈 Hasil dan Validasi F0")

    if "df_parameter" not in st.session_state:
        st.warning("❗ Silakan input data parameter terlebih dahulu.")
        return

    df = st.session_state.df_parameter.copy()

    # Hitung F0
    temps = df['suhu'].tolist()
    f0_cumsum = calculate_f0(temps)
    df['F0'] = f0_cumsum

    # Cek validasi
    valid = check_minimum_holding_time(temps)
    status_validasi = "✅ Validasi BERHASIL" if valid else "❌ Validasi GAGAL"

    st.subheader("📌 Ringkasan Hasil F0")
    st.write(f"Total F0: **{f0_cumsum[-1]:.2f}**")
    st.write(f"Status: **{status_validasi}**")

    st.subheader("📊 Grafik Suhu & F0")
    fig, ax1 = plt.subplots()
    ax1.plot(df['menit'], df['suhu'], color='red', label='Suhu (°C)')
    ax1.set_xlabel("Menit")
    ax1.set_ylabel("Suhu (°C)", color='red')
    ax2 = ax1.twinx()
    ax2.plot(df['menit'], df['F0'], color='blue', label='F₀')
    ax2.set_ylabel("F₀", color='blue')
    st.pyplot(fig)

    st.subheader("✍️ Paraf Manual")
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#ffffff",
        height=150,
        width=400,
        drawing_mode="freedraw",
        key="paraf_canvas"
    )

    st.subheader("📅 Unduh Laporan PDF")
    if st.button("Unduh PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(200, 10, "Laporan Proses Retort", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.ln(5)

        # Ringkasan
        pdf.cell(200, 10, f"Total F₀: {f0_cumsum[-1]:.2f}", ln=True)
        pdf.cell(200, 10, f"Status Validasi: {status_validasi}", ln=True)

        # Data tabel parameter
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(200, 10, "Data Parameter Proses per Menit", ln=True)
        pdf.set_font("Arial", size=9)
        for index, row in df.iterrows():
            pdf.cell(200, 8, f"Menit {row['menit']}: Suhu={row['suhu']}°C | Tekanan={row['tekanan']} bar | F₀={row['F0']:.2f}", ln=True)

        # Footnote
        pdf.ln(5)
        pdf.set_font("Arial", size=8)
        pdf.cell(200, 10, "Proses retort dilakukan oleh Rumah Retort Bersama", ln=True, align='C')

        # Download
        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        st.download_button(
            label="📄 Simpan PDF",
            data=pdf_output.getvalue(),
            file_name=f"Laporan_F0_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime='application/pdf'
        )
