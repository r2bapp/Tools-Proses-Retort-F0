import streamlit as st
import pandas as pd
import sqlite3
import datetime
from fpdf import FPDF
import io
import matplotlib.pyplot as plt
from PIL import Image
import base64
import os

# ----------------------------
# KONFIGURASI
# ----------------------------
DB_PATH = "data_retort.db"
LOGO_PATH = "R2B.png"
F0_REFERENCE_TEMP = 121.1
Z_VALUE = 10
AUTHORIZED_USERS = ["bagoes", "dimas", "iwan"]

# ----------------------------
# SISTEM LOGIN SEDERHANA BERDASARKAN NAMA
# ----------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 Login Pengguna")
    username_input = st.text_input("Masukkan nama pengguna (bagoes / dimas / iwan)")
    login_button = st.button("Login")

    if login_button:
        if username_input.lower() in AUTHORIZED_USERS:
            st.session_state.logged_in = True
            st.session_state.username = username_input.lower()
            st.experimental_rerun()
        else:
            st.error("Nama tidak dikenali. Silakan coba lagi.")
else:
    st.sidebar.success(f"👋 Selamat datang, {st.session_state.username.capitalize()}")

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
# SIMPAN DATA PELANGGAN
# ----------------------------
def save_data_pelanggan(data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO pelanggan (nama, tanggal, sesi, batch, total_waktu,
        jenis_produk, jumlah_awal, jumlah_akhir, basket1, basket2, basket3, petugas, paraf)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    pelanggan_id = c.lastrowid
    conn.close()
    return pelanggan_id

# ----------------------------
# SIMPAN DATA F0
# ----------------------------
def save_f0_data(pelanggan_id, df):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for _, row in df.iterrows():
        c.execute("""
            INSERT INTO f0_data (pelanggan_id, menit, suhu, tekanan, keterangan, f0)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (pelanggan_id, row['menit'], row['suhu'], row['tekanan'], row['keterangan'], row['f0']))
    conn.commit()
    conn.close()

# ----------------------------
# HITUNG F0
# ----------------------------
def calculate_f0(dataframe):
    f0_values = []
    for i in range(len(dataframe)):
        t = dataframe.loc[i, 'suhu']
        delta_t = 1  # diasumsikan 1 menit interval antar data
        f0_i = delta_t * 10 ** ((t - F0_REFERENCE_TEMP) / Z_VALUE)
        f0_values.append(round(f0_i, 3))
    dataframe['f0'] = f0_values
    total_f0 = round(sum(f0_values), 2)
    return dataframe, total_f0

# ----------------------------
# EKSPOR PDF
# ----------------------------
def export_pdf(pelanggan, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Laporan Proses Retort - R2B", ln=True, align='C')
    for i, val in enumerate(pelanggan):
        pdf.cell(200, 10, txt=f"{i+1}. {val}", ln=True)
    pdf.cell(200, 10, txt="", ln=True)
    pdf.cell(200, 10, txt="Data Proses:", ln=True)
    for i, row in df.iterrows():
        pdf.cell(200, 10, txt=f"Menit {row['menit']}: Suhu={row['suhu']}°C, Tekanan={row['tekanan']} kg/cm2, F0={row['f0']}", ln=True)
    return pdf.output(dest='S').encode('latin1')

# ----------------------------
# UI UTAMA
# ----------------------------
if st.session_state.logged_in:
    st.set_page_config(page_title="Retort Tools - R2B", layout="centered", page_icon=":fire:")
    st.image(LOGO_PATH, width=120)
    st.title("📋 Tools Input & F0 Retort | Rumah Retort Bersama")

    with st.form("form_input"):
        st.header("1️⃣ Data Pelanggan")
        nama = st.text_input("Nama Pelanggan")
        tanggal = st.date_input("Tanggal Proses", value=datetime.date.today())
        no_sesi = st.text_input("No Sesi")
        no_batch = st.text_input("No Batch")
        total_waktu = st.number_input("Total Waktu Retort (menit)", 0, 300)
        jenis_produk = st.text_area("Jenis Produk (bisa lebih dari satu)")
        jumlah_awal = st.number_input("Jumlah Produk Awal", 0)
        jumlah_akhir = st.number_input("Jumlah Produk Akhir", 0)
        basket1 = st.number_input("Jumlah Basket 1", 0, 100)
        basket2 = st.number_input("Jumlah Basket 2", 0, 100)
        basket3 = st.number_input("Jumlah Basket 3", 0, 100)
        petugas = st.text_input("Petugas")
        paraf = st.text_input("Paraf")

        st.header("2️⃣ Input Parameter Proses (60 Menit)")
        df_input = pd.DataFrame({
            'menit': list(range(1, 61)),
            'suhu': [0.0]*60,
            'tekanan': [0.0]*60,
            'keterangan': ['']*60
        })
        edited_df = st.data_editor(df_input, num_rows="fixed")

        submitted = st.form_submit_button("💾 Simpan & Hitung F0")

    if submitted:
        pelanggan_tuple = (nama, str(tanggal), no_sesi, no_batch, total_waktu,
                        jenis_produk, jumlah_awal, jumlah_akhir, basket1, basket2, basket3, petugas, paraf)
        pelanggan_id = save_data_pelanggan(pelanggan_tuple)

        df_hasil, total_f0 = calculate_f0(edited_df)
        save_f0_data(pelanggan_id, df_hasil)

        st.success(f"Data berhasil disimpan. Nilai Total F0: {total_f0}")

        csv = df_hasil.to_csv(index=False).encode('utf-8')
        pdf_data = export_pdf(pelanggan_tuple, df_hasil)

        st.download_button("⬇️ Download CSV", data=csv, file_name="data_f0.csv", mime="text/csv")
        st.download_button("⬇️ Download PDF", data=pdf_data, file_name="laporan_retort.pdf", mime="application/pdf")

    # ----------------------------
    # DASHBOARD F0
    # ----------------------------
    st.header("📈 Dashboard Ringkasan F0")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT pelanggan.id, nama, tanggal, total_waktu FROM pelanggan ORDER BY id DESC LIMIT 5")
    data = c.fetchall()
    st.table(pd.DataFrame(data, columns=["ID", "Nama", "Tanggal", "Total Waktu"]))

    c.execute("SELECT pelanggan_id, SUM(f0) FROM f0_data GROUP BY pelanggan_id ORDER BY pelanggan_id DESC LIMIT 5")
    f0s = c.fetchall()
    if f0s:
        ids, f0vals = zip(*f0s)
        fig, ax = plt.subplots()
        ax.plot(ids, f0vals, marker='o')
        ax.axhline(y=3.0, color='r', linestyle='--', label='Batas Minimal F0')
        ax.set_title("Nilai F0 Tiap Sesi")
        ax.set_xlabel("ID Sesi")
        ax.set_ylabel("Total F0")
        ax.legend()
        st.pyplot(fig)

    conn.close()
