# app.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, time
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
import os

DB_PATH = "retort_data.db"

# Inisialisasi database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pelanggan (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nama TEXT,
                    alamat TEXT,
                    no_hp TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS hasil_f0 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tanggal TEXT,
                    waktu TEXT,
                    suhu REAL,
                    tekanan REAL,
                    keterangan TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jumlah_awal INTEGER,
                    basket1 INTEGER,
                    basket2 INTEGER,
                    basket3 INTEGER,
                    jumlah_akhir INTEGER,
                    user TEXT,
                    tanda_tangan TEXT
                )''')
    conn.commit()
    conn.close()

# Simpan data pelanggan
def simpan_pelanggan(nama, alamat, no_hp):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO pelanggan (nama, alamat, no_hp) VALUES (?, ?, ?)", (nama, alamat, no_hp))
    conn.commit()
    conn.close()

# Simpan hasil pantauan
def simpan_data_hasil_f0(tanggal, waktu, suhu, tekanan, keterangan):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO hasil_f0 (tanggal, waktu, suhu, tekanan, keterangan) VALUES (?, ?, ?, ?, ?)",
              (tanggal, waktu, suhu, tekanan, keterangan))
    conn.commit()
    conn.close()

# Simpan metadata
def simpan_metadata(jumlah_awal, b1, b2, b3, jumlah_akhir, user, tanda_tangan_path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO metadata (jumlah_awal, basket1, basket2, basket3, jumlah_akhir, user, tanda_tangan) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (jumlah_awal, b1, b2, b3, jumlah_akhir, user, tanda_tangan_path))
    conn.commit()
    conn.close()

# Fungsi hitung F0
import numpy as np
def calculate_f0(df, T_ref=121.1, z=10):
    df = df[df['suhu'] > 90].copy()
    if df.empty:
        return pd.DataFrame(), 0.0
    df['dt'] = 1  # diasumsikan tiap menit
    df['log_reduction'] = 10 ** ((df['suhu'] - T_ref) / z)
    df['f0'] = df['log_reduction'] * df['dt']
    df['F0_total'] = df['f0'].cumsum()
    total_f0 = df['F0_total'].iloc[-1]
    return df, total_f0

# Generate PDF laporan
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Laporan Proses Retort", 0, 1, "C")
        self.set_font("Arial", "", 10)
        self.cell(0, 10, "Diproses oleh Rumah Retort Bersama", 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Halaman {self.page_no()}", 0, 0, "C")

    def laporan(self, df, total_f0, meta, tanda_path):
        self.add_page()
        self.set_font("Arial", "", 10)
        self.cell(0, 10, f"Tanggal: {datetime.now().strftime('%d-%m-%Y')}", 0, 1)
        self.cell(0, 10, f"User: {meta['user']}", 0, 1)
        self.cell(0, 10, f"Jumlah Awal: {meta['jumlah_awal']} | Basket 1: {meta['b1']} | Basket 2: {meta['b2']} | Basket 3: {meta['b3']}", 0, 1)
        self.cell(0, 10, f"Jumlah Akhir: {meta['jumlah_akhir']}", 0, 1)
        self.ln(5)
        self.cell(0, 10, "Data Pantauan:", 0, 1)

        for i in range(len(df)):
            row = df.iloc[i]
            self.cell(0, 8, f"{row['waktu']} | Suhu: {row['suhu']} C | Tekanan: {row['tekanan']} | F0: {row['f0']:.2f}", 0, 1)
        self.ln(5)
        self.cell(0, 10, f"Total F0: {total_f0:.2f}", 0, 1)

        if tanda_path and os.path.exists(tanda_path):
            self.image(tanda_path, x=150, y=self.get_y(), w=40)
            self.ln(40)

# Halaman utama
init_db()
st.set_page_config(layout="wide")
st.title("Tools Proses Retort - Rumah Retort Bersama")

# Login user
user = st.selectbox("Login sebagai:", ["", "bagoes", "iwan", "dimas"])
if user == "":
    st.warning("Silakan login terlebih dahulu")
    st.stop()

st.success(f"Login sebagai {user}")

# Input metadata
jumlah_awal = st.number_input("Jumlah Awal Produk", min_value=0)
b1 = st.number_input("Isi Basket 1", min_value=0)
b2 = st.number_input("Isi Basket 2", min_value=0)
b3 = st.number_input("Isi Basket 3", min_value=0)
jumlah_akhir = st.number_input("Jumlah Akhir Produk", min_value=0)

# Input data pantauan suhu
st.subheader("Input Data Pantauan Tiap Menit")
data = []
for i in range(3):  # contoh 3 baris input
    waktu = st.time_input(f"Waktu ke-{i+1}", key=f"waktu{i}")
    if datetime.combine(datetime.today(), waktu) - datetime.combine(datetime.today(), time(0, 0)) > timedelta(hours=2):
        st.error("Waktu tidak boleh lebih dari 2 jam")
        st.stop()
    suhu = st.number_input(f"Suhu ke-{i+1} (°C)", key=f"suhu{i}")
    tekanan = st.number_input(f"Tekanan ke-{i+1} (bar)", key=f"tekanan{i}")
    ket = st.text_input(f"Keterangan ke-{i+1}", key=f"ket{i}")
    data.append({"waktu": waktu.strftime("%H:%M"), "suhu": suhu, "tekanan": tekanan, "keterangan": ket})

# Simpan ke database dan hitung F0
if st.button("Hitung dan Simpan"):
    tanggal = datetime.now().strftime("%Y-%m-%d")
    for row in data:
        simpan_data_hasil_f0(tanggal, row['waktu'], row['suhu'], row['tekanan'], row['keterangan'])

    df = pd.DataFrame(data)
    df_hasil, total_f0 = calculate_f0(df)

    # Gambar tanda tangan manual
    st.subheader("Tanda Tangan")
    canvas_result = st_canvas(
        fill_color="#000000",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=150,
        drawing_mode="freedraw",
        key="canvas",
    )
    tanda_path = None
    if canvas_result.image_data is not None:
        from PIL import Image
        image = Image.fromarray((canvas_result.image_data).astype('uint8'))
        tanda_path = f"tanda_tangan_{user}.png"
        image.save(tanda_path)

    simpan_metadata(jumlah_awal, b1, b2, b3, jumlah_akhir, user, tanda_path)

    # Buat PDF
    pdf = PDF()
    pdf.laporan(df_hasil, total_f0, {
        "jumlah_awal": jumlah_awal,
        "b1": b1, "b2": b2, "b3": b3,
        "jumlah_akhir": jumlah_akhir,
        "user": user
    }, tanda_path)

    output_path = f"laporan_retort_{datetime.now().strftime('%d%m%Y_%H%M%S')}.pdf"
    pdf.output(output_path)

    with open(output_path, "rb") as f:
        st.download_button("📄 Unduh Laporan PDF", f, file_name=output_path)

    st.success("Data disimpan dan PDF berhasil dibuat!")
