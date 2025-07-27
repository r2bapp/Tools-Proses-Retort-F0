import streamlit as st
from streamlit_drawable_canvas import st_canvas
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime, time, timedelta
import io
import sqlite3
import os

# === DATABASE ===
DB_PATH = "retort_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS retort_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT,
            no_hp TEXT,
            nama_umkm TEXT,
            nama_produk TEXT,
            jumlah_awal INTEGER,
            basket1 INTEGER,
            basket2 INTEGER,
            basket3 INTEGER,
            jumlah_akhir INTEGER,
            suhu_data TEXT,
            total_f0 REAL,
            berhasil INTEGER,
            waktu_input TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# === FUNGSI HITUNG F0 ===
def calculate_f0(temps, T_ref=121.1, z=10):
    f0_values = []
    for T in temps:
        if T < 90:
            f0_values.append(0)
        else:
            f0_values.append(10 ** ((T - T_ref) / z))
    return np.cumsum(f0_values)

def check_minimum_holding_time(temps, min_temp=121.1, min_duration=3):
    holding_minutes = 0
    for t in temps:
        if t >= min_temp:
            holding_minutes += 1
        else:
            holding_minutes = 0
        if holding_minutes >= min_duration:
            return True
    return False

# === GENERATE PDF DENGAN GRAFIK & FOOTNOTE ===
def generate_pdf(data, total_f0, success, f0_plot):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Laporan Hasil Proses Retort", ln=True, align="C")
    pdf.cell(200, 10, txt=datetime.now().strftime("%Y-%m-%d %H:%M"), ln=True, align="C")
    pdf.ln(5)

    for key, val in data.items():
        pdf.cell(100, 10, txt=f"{key}: {val}", ln=True)

    pdf.cell(100, 10, txt=f"Total F₀: {total_f0:.2f}", ln=True)
    pdf.cell(100, 10, txt=f"Validasi Suhu ≥121.1°C selama ≥3 menit: {'✅' if success else '❌'}", ln=True)

    pdf.ln(5)

    # Simpan grafik ke buffer
    buf = io.BytesIO()
    f0_plot.savefig(buf, format='PNG')
    buf.seek(0)
    pdf.image(buf, x=10, y=None, w=180)

    pdf.ln(5)
    pdf.set_font("Arial", style='I', size=10)
    pdf.multi_cell(0, 10, txt="Proses Retort Dilakukan Oleh Rumah Retort Bersama", align="C")

    return pdf.output(dest='S').encode('latin1')

# === HALAMAN UTAMA ===
st.set_page_config(page_title="Retort F0 R2B", layout="centered")
st.title("🚀 Kalkulator F₀ Proses Retort – Rumah Retort Bersama")

with st.form("retort_form"):
    st.subheader("📋 Input Data Proses")
    tanggal = st.date_input("Tanggal Proses", value=datetime.today())
    no_hp = st.text_input("Nomor HP")
    nama_umkm = st.text_input("Nama UMKM")
    nama_produk = st.text_input("Nama Produk")

    jumlah_awal = st.number_input("Jumlah Produk Awal", min_value=0)
    basket1 = st.number_input("Jumlah Basket 1", min_value=0)
    basket2 = st.number_input("Jumlah Basket 2", min_value=0)
    basket3 = st.number_input("Jumlah Basket 3", min_value=0)

    st.subheader("🌡️ Suhu Proses per Menit")
    suhu_input = st.text_area("Masukkan data suhu (pisahkan dengan koma)", placeholder="121.5, 122.1, 123.0, ...")
    
    jumlah_akhir = st.number_input("Jumlah Produk Akhir", min_value=0)

    submitted = st.form_submit_button("Hitung F₀")

if submitted:
    try:
        temps = list(map(float, suhu_input.split(",")))
        temps = [round(t, 2) for t in temps]

        total_f0_array = calculate_f0(temps)
        total_f0 = total_f0_array[-1] if len(total_f0_array) else 0
        success = check_minimum_holding_time(temps)

        st.success(f"✅ Total F₀: {total_f0:.2f}")
        st.info(f"Validasi Suhu ≥121.1°C selama ≥3 menit: {'✅ Ya' if success else '❌ Tidak'}")

        # Grafik
        fig, ax = plt.subplots()
        ax.plot(range(len(total_f0_array)), total_f0_array, marker='o')
        ax.set_title("Grafik Nilai F₀")
        ax.set_xlabel("Menit ke-")
        ax.set_ylabel("F₀")
        st.pyplot(fig)

        # Simpan ke database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO retort_data (tanggal, no_hp, nama_umkm, nama_produk, jumlah_awal, basket1, basket2, basket3, jumlah_akhir, suhu_data, total_f0, berhasil, waktu_input)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(tanggal), no_hp, nama_umkm, nama_produk, jumlah_awal, basket1, basket2, basket3,
            jumlah_akhir, ','.join(map(str, temps)), total_f0, int(success),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()

        # PDF download
        data_dict = {
            "Tanggal": str(tanggal),
            "Nomor HP": no_hp,
            "Nama UMKM": nama_umkm,
            "Nama Produk": nama_produk,
            "Jumlah Awal": jumlah_awal,
            "Basket 1": basket1,
            "Basket 2": basket2,
            "Basket 3": basket3,
            "Jumlah Akhir": jumlah_akhir
        }

        pdf_bytes = generate_pdf(data_dict, total_f0, success, fig)
        st.download_button("📥 Unduh PDF Laporan", data=pdf_bytes, file_name="laporan_retort.pdf", mime="application/pdf")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses data: {e}")
