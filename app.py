import streamlit as st
import sqlite3
from datetime import date
import math
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import base64
from PIL import Image
import os

DB_PATH = "/mnt/data/retort_data.db"
LOGO_PATH = "R2B.png"

TB = 121.1  # suhu referensi dalam °C
Z = 10       # nilai Z standar

def save_data_pelanggan(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pelanggan (nama, tanggal_proses, no_sesi, no_batch, total_waktu,
                               jenis_produk, jumlah_awal, jumlah_akhir, petugas, paraf)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    pelanggan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pelanggan_id

def save_durasi(pelanggan_id, durasi):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO durasi_proses (pelanggan_id, venting, cut, holding, cooling)
        VALUES (?, ?, ?, ?, ?)
    """, (pelanggan_id, *durasi))
    conn.commit()
    conn.close()

def save_basket(pelanggan_id, data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO basket_produk (pelanggan_id, basket1, basket2, basket3,
                                   produk_berhasil, produk_gagal, keterangan)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (pelanggan_id, *data))
    conn.commit()
    conn.close()

def save_pantauan(pelanggan_id, pantauan):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for row in pantauan:
        cursor.execute("""
            INSERT INTO pantauan_parameter (pelanggan_id, menit, suhu, tekanan, keterangan)
            VALUES (?, ?, ?, ?, ?)
        """, (pelanggan_id, *row))
    conn.commit()
    conn.close()

def hitung_f0(pantauan):
    delta_t = 1  # interval tiap menit
    f0 = 0
    for row in pantauan:
        suhu = row[1]
        if suhu > 0:
            f0 += delta_t * math.pow(10, (suhu - TB) / Z)
    return round(f0, 2)

def save_f0(pelanggan_id, f0):
    status = "Tercapai" if f0 >= 3.0 else "Tidak Tercapai"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO hasil_f0 (pelanggan_id, nilai_f0, status)
        VALUES (?, ?, ?)
    """, (pelanggan_id, f0, status))
    conn.commit()
    conn.close()
    return status

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pelanggan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT,
            tanggal TEXT,
            sesi TEXT,
            batch TEXT,
            total_waktu INTEGER,
            jenis_produk TEXT,
            jumlah_awal INTEGER,
            jumlah_akhir INTEGER,
            petugas TEXT,
            paraf TEXT
        )
    """)
    # Tambahkan juga pembuatan tabel lainnya...
    conn.commit()
    conn.close()

# Panggil fungsi ini saat app diload
init_db()

def export_csv(pelanggan_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM pantauan_parameter WHERE pelanggan_id={pelanggan_id}", conn)
    conn.close()
    return df.to_csv(index=False).encode('utf-8')

def export_pdf(pelanggan_id, nilai_f0, status):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM pantauan_parameter WHERE pelanggan_id={pelanggan_id}", conn)
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=10, y=8, w=30)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Laporan Retort R2B", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Nilai F0: {nilai_f0} ({status})", ln=2, align='C')
    pdf.ln(10)
    for index, row in df.iterrows():
        pdf.cell(0, 10, txt=f"Menit {row['menit']}: Suhu={row['suhu']}°C, Tekanan={row['tekanan']} kg/cm2", ln=1)
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer

def show_dashboard():
    st.header("📊 Dashboard Hasil Retort")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT p.nama, p.tanggal_proses, h.nilai_f0, h.status FROM pelanggan p JOIN hasil_f0 h ON p.id=h.pelanggan_id ORDER BY p.tanggal_proses DESC", conn)
    conn.close()
    st.dataframe(df)
    st.bar_chart(df.set_index("nama")["nilai_f0"])

st.image(LOGO_PATH, width=120)
st.title("🧪 Form Pelaporan Proses Retort - R2B")

with st.form("form_pelaporan"):
    st.subheader("Data Pelanggan & Proses")
    nama = st.text_input("Nama Pelanggan")
    tanggal = st.date_input("Tanggal Proses", value=date.today())
    no_sesi = st.text_input("No Sesi")
    no_batch = st.text_input("No Batch")
    total_waktu = st.number_input("Total Waktu Retort (menit)", 0)
    jenis_produk = st.text_area("Jenis Produk (pisahkan dengan koma jika lebih dari satu)")
    jumlah_awal = st.number_input("Jumlah Produk Awal", 0)
    jumlah_akhir = st.number_input("Jumlah Produk Akhir", 0)
    petugas = st.text_input("Petugas Yang Mengerjakan")
    paraf = st.text_input("Paraf (Tanda Tangan)")

    st.subheader("Durasi Tiap Proses")
    venting = st.number_input("Venting (menit)", 0)
    cut = st.number_input("CUT (menit)", 0)
    holding = st.number_input("Holding (menit)", 0)
    cooling = st.number_input("Cooling (menit)", 0)

    st.subheader("Data Basket Produk")
    basket1 = st.text_input("Isi Basket 1")
    basket2 = st.text_input("Isi Basket 2")
    basket3 = st.text_input("Isi Basket 3")
    produk_berhasil = st.number_input("Produk Berhasil Retort", 0)
    produk_gagal = st.number_input("Produk Gagal Retort", 0)
    keterangan_gagal = st.text_area("Keterangan Gagal dan Tindak Lanjut")

    st.subheader("Pantauan Retort Tiap Menit")
    pantauan_data = []
    for menit in range(1, 61):
        with st.expander(f"Menit ke-{menit}"):
            suhu = st.number_input(f"Suhu (°C) - menit {menit}", 0.0, 150.0, step=0.1, key=f"suhu_{menit}")
            tekanan = st.number_input(f"Tekanan (kg/cm²) - menit {menit}", 0.0, 1.7, step=0.01, key=f"tekanan_{menit}")
            ket = st.text_input(f"Keterangan - menit {menit}", key=f"ket_{menit}")
            pantauan_data.append((menit, suhu, tekanan, ket))

    submitted = st.form_submit_button("Simpan Data")
    if submitted:
        pelanggan_id = save_data_pelanggan((nama, str(tanggal), no_sesi, no_batch, total_waktu,
                                            jenis_produk, jumlah_awal, jumlah_akhir, petugas, paraf))
        save_durasi(pelanggan_id, (venting, cut, holding, cooling))
        save_basket(pelanggan_id, (basket1, basket2, basket3, produk_berhasil, produk_gagal, keterangan_gagal))
        save_pantauan(pelanggan_id, pantauan_data)
        nilai_f0 = hitung_f0(pantauan_data)
        status = save_f0(pelanggan_id, nilai_f0)

        st.success(f"✅ Data berhasil disimpan! Nilai F0: {nilai_f0} ({status})")

        csv = export_csv(pelanggan_id)
        st.download_button("⬇️ Download CSV", data=csv, file_name="pantauan_f0.csv", mime="text/csv")

        pdf = export_pdf(pelanggan_id, nilai_f0, status)
        st.download_button("⬇️ Download PDF", data=pdf, file_name="laporan_retort.pdf")

show_dashboard()
