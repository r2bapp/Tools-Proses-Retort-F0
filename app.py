import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta, time
from fpdf import FPDF
import os

# ---------- Konstanta ----------
T_REF = 121.1  # Suhu referensi (°C)
Z = 10  # Faktor z (°C)
DB_PATH = "data_retort.db"

# ---------- Inisialisasi Database ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS hasil_retort (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pelanggan TEXT,
        nama_umkm TEXT
        nama_produk TEXT
        nomor_kontak TEXT
        jumlah_awal INTEGER,
        basket1 INTEGER,
        basket2 INTEGER,
        basket3 INTEGER,
        jumlah_akhir INTEGER,
        total_f0 REAL,
        tanggal TEXT,
        data_pantauan TEXT
    )''')
    conn.commit()
    conn.close()

# ---------- Fungsi Perhitungan F0 ----------
def calculate_f0(df):
    f0_values = []
    for index, row in df.iterrows():
        T = row['Suhu (°C)']
        if T > 90:
            f = 10 ** ((T - T_REF) / Z)
        else:
            f = 0
        f0_values.append(f)
    df['F0'] = f0_values
    df['F0 Akumulatif'] = np.cumsum(f0_values)
    return df, df['F0 Akumulatif'].iloc[-1] if not df.empty else 0

# ---------- Fungsi PDF ----------
def generate_pdf(pelanggan, nama_umkm, nama_produk, nomor_kontak, jumlah_awal, basket1, basket2, basket3, jumlah_akhir, df, total_f0):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Laporan Proses Retort", ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Tanggal: {datetime.today().strftime('%d-%m-%Y')}", ln=True)
    pdf.cell(200, 10, f"Nama Pelanggan: {pelanggan}", ln=True)
    pdf.cell(200, 10, f"Nama UMKM : {nama_umkm}", ln=True)
    pdf.cell(200, 10, f"Nama Produk : {nama_produk}", ln=True)
    pdf.cell(200, 10, f"Nomor Kontak : {nomor_kontak}", ln=True)
    pdf.cell(200, 10, f"Jumlah Awal Produk: {jumlah_awal}", ln=True)
    pdf.cell(200, 10, f"Basket 1: {basket1} | Basket 2: {basket2} | Basket 3: {basket3}", ln=True)
    pdf.cell(200, 10, f"Jumlah Produk Akhir: {jumlah_akhir}", ln=True)
    pdf.cell(200, 10, f"Total F0: {round(total_f0, 2)} menit", ln=True)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "\nData Pantauan Retort", ln=True)

    pdf.set_font("Arial", size=10)
    col_width = 48
    pdf.cell(col_width, 10, "Waktu", 1)
    pdf.cell(col_width, 10, "Suhu (°C)", 1)
    pdf.cell(col_width, 10, "Tekanan", 1)
    pdf.cell(col_width, 10, "Keterangan", 1)
    pdf.ln()

    for _, row in df.iterrows():
        pdf.cell(col_width, 10, str(row['Waktu']), 1)
        pdf.cell(col_width, 10, str(row['Suhu (°C)']), 1)
        pdf.cell(col_width, 10, str(row['Tekanan (psi)']), 1)
        pdf.cell(col_width, 10, str(row['Keterangan']), 1)
        pdf.ln()

    pdf.ln(5)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(200, 10, "Diproses oleh Rumah Retort Bersama", ln=True, align="C")

    output_path = f"laporan_retort_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(output_path)
    return output_path

# ---------- Aplikasi Streamlit ----------
st.set_page_config(page_title="Proses Retort R2B", layout="wide")
st.title("Tools Proses Retort & Penghitung F0 |by Rumah Retort Bersama")

# ---------- Login ----------
username = st.text_input("Masukkan Nama (bagoes, iwan, dimas):")
if username.lower() not in ["bagoes", "iwan", "dimas"]:
    st.warning("Hanya user yang diizinkan yang bisa masuk.")
    st.stop()

# ---------- Input Data ----------
st.header("Input Data Pelanggan dan Proses")
pelanggan = st.text_input("Nama Pelanggan")
nama_umkm = st.text_input("Nama UMKM")
nama_produk = st.text_input("Nama Produk")
nomor_kontak = st.number_input("Nomor Kontak", min_value=0)
tanggal = st.date_input("Tanggal Proses")
jumlah_awal = st.number_input("Jumlah Awal Produk", min_value=0)
basket1 = st.number_input("Jumlah Basket 1", min_value=0)
basket2 = st.number_input("Jumlah Basket 2", min_value=0)
basket3 = st.number_input("Jumlah Basket 3", min_value=0)

st.subheader("Pantauan Suhu, Tekanan dan Keterangan (Per Menit)")
data = {
    "Waktu": [],
    "Suhu (°C)": [],
    "Tekanan (psi)": [],
    "Keterangan": []
}

for i in range(10):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        waktu = st.time_input(f"Waktu {i+1}", key=f"waktu_{i}")
    with col2:
        suhu = st.number_input(f"Suhu °C {i+1}", key=f"suhu_{i}")
    with col3:
        tekanan = st.number_input(f"Tekanan {i+1}", key=f"tekanan_{i}")
    with col4:
        ket = st.text_input(f"Keterangan {i+1}", key=f"ket_{i}")
    data['Waktu'].append(waktu.strftime("%H:%M"))
    data['Suhu (°C)'].append(suhu)
    data['Tekanan (psi)'].append(tekanan)
    data['Keterangan'].append(ket)

jumlah_akhir = st.number_input("Jumlah Produk Akhir", min_value=0)

# ---------- Tampilkan dan Hitung F0 ----------
df_input = pd.DataFrame(data)
st.subheader("Data Pantauan")
st.dataframe(df_input)

if st.button("Hitung & Simpan"):
    df_hasil, total_f0 = calculate_f0(df_input)
    st.success(f"Total Nilai F0: {round(total_f0,2)} menit")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO hasil_retort (pelanggan, nama_umkm, nama_produk, nomor_kontak, jumlah_awal, basket1, basket2, basket3, jumlah_akhir, total_f0, tanggal, data_pantauan) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (pelanggan, nama_umkm, nama_produk, nomor_kontak, jumlah_awal, basket1, basket2, basket3, jumlah_akhir, total_f0, tanggal.strftime("%Y-%m-%d"), df_input.to_json()))
    conn.commit()
    conn.close()

    path_pdf = generate_pdf(pelanggan, nama_umkm, nama_produk, str(nomor_kontak), jumlah_awal, basket1, basket2, basket3, jumlah_akhir, df_hasil, total_f0)
    with open(path_pdf, "rb") as f:
        st.download_button("📥 Unduh Laporan PDF", f, file_name=path_pdf, mime="application/pdf")

# ---------- Inisialisasi DB ----------
init_db()
