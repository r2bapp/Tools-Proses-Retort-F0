import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta, time
from fpdf import FPDF
import matplotlib.pyplot as plt
from streamlit_drawable_canvas import st_canvas
import os

DB_PATH = "retort_data.db"

# Inisialisasi database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hasil_retort (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT,
        nama_umkm TEXT,
        nama_produk TEXT,
        no_hp TEXT,
        jumlah_awal INTEGER,
        basket1 INTEGER,
        basket2 INTEGER,
        basket3 INTEGER,
        jumlah_akhir INTEGER,
        total_f0 REAL,
        validasi TEXT
    )
    """)
    conn.commit()
    conn.close()

# Fungsi hitung F₀
def calculate_f0(temps, T_ref=121.1, z=10):
    f0_values = []
    for T in temps:
        if T < 90:
            f0_values.append(0)
        else:
            f0_values.append(10 ** ((T - T_ref) / z))
    return np.cumsum(f0_values)

# Cek suhu 121.1°C minimal 3 menit
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

def save_pdf(data_df, total_f0, valid, signature_img, grafik_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, "Laporan Hasil Proses Retort", ln=True, align='C')
    pdf.ln(10)

    fields = [
        ("Tanggal", data_df['Tanggal'][0]),
        ("Nama UMKM", data_df['Nama UMKM'][0]),
        ("Nama Produk", data_df['Nama Produk'][0]),
        ("No HP", data_df['No HP'][0]),
        ("Jumlah Awal", str(data_df['Jumlah Awal'][0])),
        ("Basket 1", str(data_df['Basket 1'][0])),
        ("Basket 2", str(data_df['Basket 2'][0])),
        ("Basket 3", str(data_df['Basket 3'][0])),
        ("Jumlah Akhir", str(data_df['Jumlah Akhir'][0])),
        ("Total F₀", f"{total_f0:.2f}"),
        ("Validasi", valid)
    ]

    for label, value in fields:
        pdf.cell(60, 10, f"{label}:", border=0)
        pdf.cell(0, 10, value, ln=True, border=0)

    pdf.ln(5)
    pdf.cell(0, 10, "Grafik F₀", ln=True)
    pdf.image(grafik_path, w=160)
    pdf.ln(5)

    if signature_img:
        pdf.cell(0, 10, "Tanda Tangan:", ln=True)
        pdf.image(signature_img, x=30, w=60)

    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, "Proses Retort Dilakukan Oleh Rumah Retort Bersama", align="C")

    output_path = "laporan_retort.pdf"
    pdf.output(output_path)
    return output_path

def app():
    st.title("📊 Tools Retort - Rumah Retort Bersama")

    st.subheader("🧾 Input Data Pelanggan dan Proses")
    with st.form("form_input"):
        tanggal = st.date_input("Tanggal Proses")
        nama_umkm = st.text_input("Nama UMKM")
        nama_produk = st.text_input("Nama Produk")
        no_hp = st.text_input("No. Handphone")
        jumlah_awal = st.number_input("Jumlah Produk Awal", min_value=0)
        basket1 = st.number_input("Isi Basket 1", min_value=0)
        basket2 = st.number_input("Isi Basket 2", min_value=0)
        basket3 = st.number_input("Isi Basket 3", min_value=0)

        st.markdown("---")
        st.subheader("📈 Input Data Pantauan per Menit")
        num_rows = st.number_input("Jumlah Data Menit", min_value=1, step=1)
        waktu = [time(hour=(i // 60), minute=(i % 60)) for i in range(int(num_rows))]
        suhu = [st.number_input(f"Suhu °C [Menit {i+1}]", key=f"suhu_{i}") for i in range(int(num_rows))]
        tekanan = [st.text_input(f"Tekanan [Menit {i+1}]", key=f"tekanan_{i}") for i in range(int(num_rows))]
        keterangan = [st.text_input(f"Keterangan [Menit {i+1}]", key=f"ket_{i}") for i in range(int(num_rows))]

        jumlah_akhir = st.number_input("Jumlah Produk Akhir", min_value=0)

        st.markdown("---")
        st.subheader("✍️ Paraf Manual (Touchscreen)")
        canvas_result = st_canvas(
            fill_color="rgba(0, 0, 0, 0)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#fff",
            update_streamlit=True,
            height=150,
            drawing_mode="freedraw",
            key="canvas"
        )

        submitted = st.form_submit_button("Proses dan Simpan")

    if submitted:
        temps_array = np.array(suhu)
        f0_array = calculate_f0(temps_array)
        total_f0 = f0_array[-1]
        validasi = "✅ Valid" if check_minimum_holding_time(temps_array) else "❌ Tidak Valid"

        st.success(f"Total F₀: {total_f0:.2f} | Validasi: {validasi}")

        # Simpan grafik F0
        plt.figure()
        plt.plot(f0_array, label="F₀")
        plt.xlabel("Menit ke-")
        plt.ylabel("F₀")
        plt.title("Grafik F₀ per Menit")
        plt.grid()
        grafik_path = "grafik_f0.png"
        plt.savefig(grafik_path)
        st.image(grafik_path)

        # DataFrame
        data = {
            "Tanggal": [str(tanggal)],
            "Nama UMKM": [nama_umkm],
            "Nama Produk": [nama_produk],
            "No HP": [no_hp],
            "Jumlah Awal": [jumlah_awal],
            "Basket 1": [basket1],
            "Basket 2": [basket2],
            "Basket 3": [basket3],
            "Jumlah Akhir": [jumlah_akhir]
        }
        df = pd.DataFrame(data)

        # Simpan PDF
        signature_path = None
        if canvas_result.image_data is not None:
            from PIL import Image
            img = Image.fromarray((canvas_result.image_data).astype("uint8"))
            signature_path = "signature.png"
            img.save(signature_path)

        pdf_path = save_pdf(df, total_f0, validasi, signature_path, grafik_path)
        with open(pdf_path, "rb") as f:
            st.download_button("📥 Unduh Laporan PDF", f, file_name="laporan_retort.pdf")

        # Simpan ke DB
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO hasil_retort (
                tanggal, nama_umkm, nama_produk, no_hp,
                jumlah_awal, basket1, basket2, basket3, jumlah_akhir,
                total_f0, validasi
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(tanggal), nama_umkm, nama_produk, no_hp,
            jumlah_awal, basket1, basket2, basket3, jumlah_akhir,
            total_f0, validasi
        ))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    init_db()
    app()
