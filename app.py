import streamlit as st
import pandas as pd
import numpy as np
import datetime
import sqlite3
from fpdf import FPDF
import io

# Buat tabel
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS pelanggan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT, tanggal TEXT, sesi TEXT, batch TEXT, waktu_total INTEGER,
    jenis_produk TEXT, jumlah_awal INTEGER, petugas TEXT, paraf TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS proses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pelanggan_id INTEGER, venting INTEGER, cut INTEGER, holding INTEGER, cooling INTEGER,
    FOREIGN KEY(pelanggan_id) REFERENCES pelanggan(id))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS produk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pelanggan_id INTEGER, basket1 TEXT, basket2 TEXT, basket3 TEXT,
    berhasil INTEGER, gagal INTEGER, keterangan TEXT, jumlah_akhir INTEGER,
    FOREIGN KEY(pelanggan_id) REFERENCES pelanggan(id))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS parameter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pelanggan_id INTEGER, menit INTEGER, tekanan REAL, suhu REAL, keterangan TEXT,
    FOREIGN KEY(pelanggan_id) REFERENCES pelanggan(id))''')
conn.commit()

# Login sederhana
def login():
    st.title("Login Operator Retort")
    username = st.text_input("Masukkan nama pengguna (iwan, bagoes, dimas)")
    if st.button("Login"):
        if username in ["iwan", "bagoes", "dimas"]:
            st.session_state["user"] = username
        else:
            st.error("Nama pengguna tidak dikenal")

if "user" not in st.session_state:
    login()
else:
    st.sidebar.success(f"Login sebagai: {st.session_state['user']}")
    menu = st.sidebar.selectbox("Navigasi", ["Input Data", "Pantauan Parameter", "Hitung F0", "Export PDF"])

    if menu == "Input Data":
        st.header("Data Pelanggan")
        with st.form("form_pelanggan"):
            nama = st.text_input("Nama Pelanggan")
            tanggal = st.date_input("Tanggal Proses", datetime.date.today())
            sesi = st.text_input("No Sesi")
            batch = st.text_input("No Batch")
            waktu_total = st.number_input("Total Waktu Retort (menit)", min_value=0)
            jenis_produk = st.text_area("Jenis Produk (pisahkan dengan koma)")
            jumlah_awal = st.number_input("Jumlah Produk Awal", min_value=0)
            petugas = st.text_input("Petugas yang mengerjakan", value=st.session_state['user'])
            paraf = st.text_input("Paraf (Tanda Tangan Digital)")

            submitted = st.form_submit_button("Simpan Data Pelanggan")
            if submitted:
                cursor.execute('''INSERT INTO pelanggan 
                    (nama, tanggal, sesi, batch, waktu_total, jenis_produk, jumlah_awal, petugas, paraf)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (nama, str(tanggal), sesi, batch, waktu_total, jenis_produk, jumlah_awal, petugas, paraf))
                conn.commit()
                st.success("Data pelanggan disimpan")

                pelanggan_id = cursor.lastrowid
                st.subheader("📦 Data Basket & Hasil Produk")
                with st.form("form_produk"):
                    basket1 = st.text_area("Isi Basket 1")
                    basket2 = st.text_area("Isi Basket 2")
                    basket3 = st.text_area("Isi Basket 3")
                    berhasil = st.number_input("Jumlah Produk Berhasil Retort", min_value=0)
                    gagal = st.number_input("Jumlah Produk Gagal Retort", min_value=0)
                    keterangan = st.text_area("Keterangan Gagal (jumlah, alasan, tindak lanjut)")
                    jumlah_akhir = st.number_input("Jumlah Produk Akhir", min_value=0)
                    simpan_produk = st.form_submit_button("Simpan Data Produk")
                    if simpan_produk:
                        cursor.execute('''
                            INSERT INTO produk (pelanggan_id, basket1, basket2, basket3, berhasil, gagal, keterangan, jumlah_akhir)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                            (pelanggan_id, basket1, basket2, basket3, berhasil, gagal, keterangan, jumlah_akhir))
                        conn.commit()
                        st.success("✅ Data produk berhasil disimpan")

    elif menu == "Pantauan Parameter":
        st.header("Input Parameter Retort per Menit")
        pelanggan_id = st.number_input("Masukkan ID Data Pelanggan", min_value=1)
        with st.form("form_param"):
            menit = st.number_input("Menit", min_value=1, max_value=60)
            tekanan = st.number_input("Tekanan (kg/cm2)", min_value=0.0, max_value=1.7)
            suhu = st.number_input("Suhu (°C)", min_value=0.0, max_value=150.0)
            keterangan = st.text_input("Keterangan")
            simpan = st.form_submit_button("Simpan Parameter")
            if simpan:
                cursor.execute('''INSERT INTO parameter (pelanggan_id, menit, tekanan, suhu, keterangan)
                                  VALUES (?, ?, ?, ?, ?)''', (pelanggan_id, menit, tekanan, suhu, keterangan))
                conn.commit()
                st.success(f"Data menit ke-{menit} disimpan")

    elif menu == "Hitung F0":
        st.header("Perhitungan Nilai F0")
        pelanggan_id = st.number_input("ID Data Pelanggan untuk Hitung F0", min_value=1)
        z = 10
        tb = 121.1
        delta_t = 1

        df = pd.read_sql_query("SELECT * FROM parameter WHERE pelanggan_id = ? ORDER BY menit", conn, params=(pelanggan_id,))
        if not df.empty:
            df["f0_contrib"] = 10 ** ((df["suhu"] - tb) / z)
            df["F0"] = df["f0_contrib"].cumsum() * delta_t
            st.line_chart(df[["F0"]])
            total_f0 = df["F0"].iloc[-1]
            st.success(f"Total Nilai F0: {round(total_f0, 2)}")

            if total_f0 >= 3:
                st.info("✅ Proses retort berhasil secara sterilisasi komersial (F0 ≥ 3)")
            else:
                st.warning("⚠️ Proses retort belum memenuhi nilai F0 yang cukup")

    elif menu == "Export PDF":
        st.header("Export Hasil Laporan ke PDF")
        pelanggan_id = st.number_input("Masukkan ID untuk Export PDF", min_value=1)
        pelanggan = pd.read_sql_query("SELECT * FROM pelanggan WHERE id = ?", conn, params=(pelanggan_id,))
        param = pd.read_sql_query("SELECT * FROM parameter WHERE pelanggan_id = ?", conn, params=(pelanggan_id,))
        produk = pd.read_sql_query("SELECT * FROM produk WHERE pelanggan_id = ?", conn, params=(pelanggan_id,))
        if not pelanggan.empty and not param.empty:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Laporan Proses Retort - Rumah Retort Bersama", ln=1, align="C")
            pdf.ln(5)
            for col in pelanggan.columns:
                pdf.cell(0, 10, f"{col}: {pelanggan[col][0]}", ln=1)
            if not produk.empty:
                pdf.ln(5)
                pdf.cell(0, 10, "Data Basket & Produk:", ln=1)
                pdf.cell(0, 8, f"Basket 1: {produk['basket1'][0]}", ln=1)
                pdf.cell(0, 8, f"Basket 2: {produk['basket2'][0]}", ln=1)
                pdf.cell(0, 8, f"Basket 3: {produk['basket3'][0]}", ln=1)
                pdf.cell(0, 8, f"Produk Berhasil: {produk['berhasil'][0]}", ln=1)
                pdf.cell(0, 8, f"Produk Gagal: {produk['gagal'][0]}", ln=1)
                pdf.cell(0, 8, f"Keterangan: {produk['keterangan'][0]}", ln=1)
                pdf.cell(0, 8, f"Jumlah Produk Akhir: {produk['jumlah_akhir'][0]}", ln=1)
            pdf.ln(5)
            pdf.cell(0, 10, "Data Parameter:", ln=1)
            for index, row in param.iterrows():
                pdf.cell(0, 8, f"Menit {row['menit']} - Suhu: {row['suhu']} °C, Tekanan: {row['tekanan']} kg/cm2", ln=1)
            pdf.set_y(-30)
            pdf.set_font("Arial", "I", 8)
            pdf.cell(0, 10, "Diproses oleh Rumah Retort Bersama", 0, 0, "C")
            pdf_output = io.BytesIO()
            pdf.output(pdf_output)
            st.download_button("Download PDF", data=pdf_output.getvalue(), file_name="laporan_retort.pdf")
