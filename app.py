import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta, time
import matplotlib.pyplot as plt
from fpdf import FPDF
import io
import os

DB_PATH = "hasil_retort.db"
USERS = ["bagoes", "iwan", "dimas"]

# -------------------- Login --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    username = st.text_input("Masukkan nama pengguna")
    if st.button("Login"):
        if username.lower() in USERS:
            st.session_state.logged_in = True
            st.session_state.user = username
        else:
            st.error("Nama tidak dikenali.")
    st.stop()

# -------------------- Inisialisasi DB --------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS hasil_retort (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pelanggan TEXT,
        nama_umkm TEXT,
        nama_produk TEXT,
        nomor_kontak TEXT,
        jumlah_awal INTEGER,
        basket1 INTEGER,
        basket2 INTEGER,
        basket3 INTEGER,
        jumlah_akhir INTEGER,
        total_f0 REAL,
        tanggal TEXT,
        data_pantauan TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------- Perhitungan F0 --------------------
def calculate_f0(df):
    T_ref = 121.1
    z = 10
    f0_values = []

    for index, row in df.iterrows():
        T = row['Suhu (°C)']
        if T > 90:
            f0 = 10 ** ((T - T_ref) / z)
        else:
            f0 = 0
        f0_values.append(f0)

    df["F0"] = f0_values
    df["F0 Akumulatif"] = df["F0"].cumsum()
    total_f0 = df["F0"].sum()
    return df, round(total_f0, 2)

# -------------------- PDF Generator --------------------
def generate_pdf(data_input, df_f0, total_f0):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Laporan Proses Retort", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Tanggal Proses: {data_input['tanggal'].strftime('%Y-%m-%d')}", ln=True, align='C')
    pdf.ln(10)

    # Informasi pelanggan
    pdf.cell(200, 10, txt=f"Pelanggan: {data_input['pelanggan']}", ln=True)
    pdf.cell(200, 10, txt=f"UMKM: {data_input['nama_umkm']} | Produk: {data_input['nama_produk']}", ln=True)
    pdf.cell(200, 10, txt=f"No. HP: {data_input['nomor_kontak']}", ln=True)
    pdf.cell(200, 10, txt=f"Jumlah Awal: {data_input['jumlah_awal']} | Basket1: {data_input['basket1']} | Basket2: {data_input['basket2']} | Basket3: {data_input['basket3']} | Jumlah Akhir: {data_input['jumlah_akhir']}", ln=True)
    pdf.ln(5)

    # Tabel data F0
    pdf.set_font("Arial", size=10)
    pdf.cell(30, 10, "Menit", 1)
    pdf.cell(30, 10, "Suhu", 1)
    pdf.cell(30, 10, "Tekanan", 1)
    pdf.cell(30, 10, "F0", 1)
    pdf.ln()

    for _, row in df_f0.iterrows():
        pdf.cell(30, 10, str(row['Menit']), 1)
        pdf.cell(30, 10, str(row['Suhu']), 1)
        pdf.cell(30, 10, str(row['Tekanan']), 1)
        pdf.cell(30, 10, f"{row['F0']:.2f}", 1)
        pdf.ln()

    pdf.ln(10)
    pdf.set_font("Arial", style='B')
    pdf.cell(200, 10, txt=f"Total Nilai F0: {total_f0:.2f}", ln=True)

    pdf.set_font("Arial", size=9)
    pdf.cell(200, 10, txt="*Diproses oleh Rumah Retort Bersama", ln=True, align='C')

    # Output ke Streamlit
    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output.read()

# -------------------- UI Input --------------------
st.title("📦 Alat Hitung F0 Proses Retort | Rumah Retort Bersama")

with st.form("form_input"):
    pelanggan = st.text_input("Nama Pelanggan")
    nama_umkm = st.text_input("Nama UMKM")
    nama_produk = st.text_input("Nama Produk")
    nomor_kontak = st.text_input("Nomor Handphone")
    tanggal = st.date_input("Tanggal Proses")
    jumlah_awal = st.number_input("Jumlah Produk Awal", min_value=0)
    basket1 = st.number_input("Isi Basket 1", min_value=0)
    basket2 = st.number_input("Isi Basket 2", min_value=0)
    basket3 = st.number_input("Isi Basket 3", min_value=0)

    st.markdown("### 📝 Input Pantauan Per Menit")
    n = st.number_input("Jumlah menit pemantauan", min_value=1, value=10)
    waktu_list, suhu_list, tekanan_list, ket_list = [], [], [], []
    for i in range(int(n)):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            waktu = st.time_input(f"Waktu ke-{i+1}", value=(datetime.combine(datetime.today(), time(0, 0)) + timedelta(minutes=i)).time(), key=f"w{i}")
        with col2:
            suhu = st.number_input(f"Suhu ke-{i+1} (°C)", key=f"s{i}")
        with col3:
            tekanan = st.number_input(f"Tekanan ke-{i+1} (psi)", key=f"p{i}")
        with col4:
            keterangan = st.text_input(f"Keterangan ke-{i+1}", key=f"k{i}")
        waktu_list.append(waktu.strftime("%H:%M"))
        suhu_list.append(suhu)
        tekanan_list.append(tekanan)
        ket_list.append(keterangan)

    jumlah_akhir = st.number_input("Jumlah Produk Akhir", min_value=0)
    submit = st.form_submit_button("💾 Proses dan Simpan")

if submit:
    df_input = pd.DataFrame({
        "Menit ke-": list(range(1, int(n)+1)),
        "Waktu": waktu_list,
        "Suhu (°C)": suhu_list,
        "Tekanan (psi)": tekanan_list,
        "Keterangan": ket_list
    })

    df_hasil, total_f0 = calculate_f0(df_input)

    # Simpan ke database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO hasil_retort (
            pelanggan, nama_umkm, nama_produk, nomor_kontak,
            jumlah_awal, basket1, basket2, basket3,
            jumlah_akhir, total_f0, tanggal, data_pantauan
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pelanggan, nama_umkm, nama_produk, nomor_kontak,
        jumlah_awal, basket1, basket2, basket3,
        jumlah_akhir, total_f0, tanggal.strftime("%Y-%m-%d"), df_input.to_json()
    ))
    conn.commit()
    conn.close()

    st.success("✅ Data berhasil diproses dan disimpan.")

    st.markdown("### 📊 Grafik F0")
    fig, ax = plt.subplots()
    ax.plot(df_hasil["Menit ke-"], df_hasil["F0 Akumulatif"], color='orange')
    ax.set_xlabel("Menit ke-")
    ax.set_ylabel("F0 Akumulatif")
    st.pyplot(fig)

    st.markdown("### 📄 Unduh PDF")
    data_input = {
        "Nama Pelanggan": pelanggan,
        "Nama UMKM": nama_umkm,
        "Nama Produk": nama_produk,
        "Nomor HP": nomor_kontak,
        "Tanggal": tanggal.strftime("%d-%m-%Y"),
        "Jumlah Awal": jumlah_awal,
        "Basket 1": basket1,
        "Basket 2": basket2,
        "Basket 3": basket3,
        "Jumlah Akhir": jumlah_akhir,
        "Total F0": total_f0
    }

    pdf_data = generate_pdf(data_input, df_hasil, total_f0)
    st.download_button("⬇️ Unduh Laporan PDF", data=pdf_data, file_name="laporan_retort.pdf", mime="application/pdf")
