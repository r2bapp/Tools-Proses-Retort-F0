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

# Halaman: Perhitungan F0

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

def hasil_f0_page():
    st.title("📈 Hasil dan Validasi F0")

    if "df_parameter" not in st.session_state:
        st.warning("❗ Silakan input data parameter terlebih dahulu.")
        return

    df = st.session_state.df_parameter

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
    ax1.set_ylabel("Suhu (°C)", color='red')
    ax2 = ax1.twinx()
    ax2.plot(df['menit'], df['F0'], color='blue', label='F₀')
    ax2.set_ylabel("F₀", color='blue')
    st.pyplot(fig)

    st.subheader("📥 Unduh Laporan PDF")
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

# ----------------------------
# UI UTAMA
# ----------------------------
st.set_page_config(page_title="Retort Tools - R2B", layout="centered", page_icon=":fire:")
st.image(LOGO_PATH, width=120)
st.title("📋 Tools Input & F0 Retort | Rumah Retort Bersama")

with st.form("form_input"):
    st.header("1️⃣ Data Pelanggan")
    nama = st.text_input("Nama Pelanggan")
    tanggal = st.date_input("Tanggal Proses", value=datetime.date.today())
    no_sesi = st.text_input("No Sesi")
    no_batch = st.text_input("No Batch")
    jenis_produk = st.text_area("Jenis Produk (bisa lebih dari satu)")
    jumlah_awal = st.number_input("Jumlah Produk Awal", 0)
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

    jumlah_akhir = st.number_input("Jumlah Produk Akhir (Input Setelah Proses)", 0)

    submitted = st.form_submit_button("💾 Simpan & Hitung F0")

if submitted:
    total_waktu = len(edited_df)
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
