import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, time
import matplotlib.pyplot as plt
from fpdf import FPDF
import io

# --- DATABASE SETUP ---
DB_PATH = "retort_data.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS hasil_retort (
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
            )''')
conn.commit()

# --- FUNCTION TO CALCULATE F0 ---
def calculate_f0(df):
    z = 10
    T_ref = 121.1
    f0_values = []
    for t in df['Suhu (°C)']:
        if t > 90:
            f = 10 ** ((t - T_ref) / z)
        else:
            f = 0
        f0_values.append(f)
    df['F0 per menit'] = f0_values
    df['Akumulasi F0'] = df['F0 per menit'].cumsum()
    total_f0 = round(df['Akumulasi F0'].iloc[-1], 2)
    return df, total_f0

# --- PDF GENERATION ---
def generate_pdf(data_input, df, total_f0):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Header
    pdf.cell(200, 10, txt="Laporan Hasil Retort", ln=True, align='C')
    pdf.cell(200, 10, txt="Diproses oleh Rumah Retort Bersama", ln=True, align='C')
    pdf.ln(5)

    # Info dasar
    tanggal_str = data_input['tanggal'].strftime('%Y-%m-%d') if 'tanggal' in data_input else '-'
    pdf.cell(200, 10, txt=f"Tanggal Proses: {tanggal_str}", ln=True)
    pdf.cell(200, 10, txt=f"Pelanggan: {data_input.get('pelanggan', '-')}", ln=True)
    pdf.cell(200, 10, txt=f"UMKM: {data_input.get('nama_umkm', '-')}", ln=True)
    pdf.cell(200, 10, txt=f"Produk: {data_input.get('nama_produk', '-')}", ln=True)
    pdf.cell(200, 10, txt=f"Nomor Kontak: {data_input.get('nomor_kontak', '-')}", ln=True)
    pdf.cell(200, 10, txt=f"Jumlah Awal: {data_input.get('jumlah_awal', '-')}", ln=True)
    pdf.cell(200, 10, txt=f"Jumlah Akhir: {data_input.get('jumlah_akhir', '-')}", ln=True)
    pdf.cell(200, 10, txt=f"Total F0: {total_f0}", ln=True)
    pdf.ln(5)

    # Grafik
    plt.figure(figsize=(5, 3))
    plt.plot(df['Waktu'], df['Akumulasi F0'], marker='o')
    plt.title('Grafik Akumulasi F0')
    plt.xlabel('Waktu')
    plt.ylabel('F0')
    plt.grid(True)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    pdf.image(buf, x=10, y=None, w=180)
    plt.close()

    return pdf.output(dest='S').encode('latin-1')

# --- STREAMLIT UI ---
st.set_page_config(layout="wide")
st.title("Tools Proses Retort - F0 Calculator |by Rumah Retort Bersama")

with st.form("input_form"):
    st.subheader("📋 Data Proses Retort")
    col1, col2 = st.columns(2)
    with col1:
        pelanggan = st.text_input("Nama Pelanggan")
        nama_umkm = st.text_input("Nama UMKM")
        nama_produk = st.text_input("Nama Produk")
        nomor_kontak = st.text_input("Nomor Kontak")
        tanggal = st.date_input("Tanggal Proses", datetime.today())
    with col2:
        jumlah_awal = st.number_input("Jumlah Awal", min_value=0)
        basket1 = st.number_input("Isi Basket 1", min_value=0)
        basket2 = st.number_input("Isi Basket 2", min_value=0)
        basket3 = st.number_input("Isi Basket 3", min_value=0)
        jumlah_akhir = st.number_input("Jumlah Akhir", min_value=0)

    st.subheader("📈 Data Pantauan per Menit")
    df_input = st.data_editor(pd.DataFrame({
        "Waktu": [],
        "Suhu (°C)": [],
        "Tekanan (Bar)": [],
        "Keterangan": []
    }), num_rows="dynamic")

    submitted = st.form_submit_button("🔍 Hitung Nilai F0")

if submitted:
    if df_input.empty:
        st.error("Masukkan data pantauan terlebih dahulu!")
    else:
        df_result, total_f0 = calculate_f0(df_input)
        data_input = {
            "tanggal": tanggal,
            "pelanggan": pelanggan,
            "nama_umkm": nama_umkm,
            "nama_produk": nama_produk,
            "nomor_kontak": nomor_kontak,
            "jumlah_awal": jumlah_awal,
            "basket1": basket1,
            "basket2": basket2,
            "basket3": basket3,
            "jumlah_akhir": jumlah_akhir
        }

        # Simpan ke DB
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO hasil_retort (pelanggan, nama_umkm, nama_produk, nomor_kontak, jumlah_awal, basket1, basket2, basket3, jumlah_akhir, total_f0, tanggal, data_pantauan) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (pelanggan, nama_umkm, nama_produk, nomor_kontak, jumlah_awal, basket1, basket2, basket3, jumlah_akhir, total_f0, tanggal.strftime("%Y-%m-%d"), df_input.to_json()))
        conn.commit()
        conn.close()

        # Tampilkan hasil dan grafik
        st.success(f"Total nilai F0: {total_f0}")
        st.dataframe(df_result)
        st.line_chart(df_result[['Akumulasi F0']])

        # Generate dan unduh PDF
        pdf_data = generate_pdf(data_input, df_result, total_f0)
        st.download_button("📥 Unduh Laporan PDF", pdf_data, file_name=f"laporan_retort_{tanggal}.pdf")
