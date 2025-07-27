from fpdf import FPDF
from io import BytesIO
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="Unduh Data PDF dan Tools menghitung F0", layout="wide")
st.title("Tools Menghitung F0 - Rumah Retort Bersama")

st.markdown("""
Aplikasi ini menghitung nilai **F₀ (F-nol)** dari data suhu per menit selama proses sterilisasi.
Gunakan input manual suhu tiap menit.
""")

# Data form
st.sidebar.header("📝 Form Data Proses")
nama_produk = st.sidebar.text_input("Nama Produk")
tanggal_proses = st.sidebar.date_input("Tanggal Proses")
nama_operator = st.sidebar.text_input("Nama Operator")
nama_alat = st.sidebar.text_input("Nama Alat Retort")

# Fungsi hitung F₀
def calculate_f0(temps, T_ref=121.1, z=10):
    f0_values = []
    for T in temps:
        if T < 90:
            f0_values.append(0)
        else:
            f0_values.append(10 ** ((T - T_ref) / z))
    return np.cumsum(f0_values)

# Fungsi cek suhu minimal 121.1°C selama ≥3 menit
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

# Pilihan metode input
input_method = st.radio("🔘 Pilih Metode Input", ["Manual"])
temps = []

if input_method == "Manual":
    st.subheader("📋 Input Manual Suhu per Menit")
    waktu = st.number_input("Jumlah menit", min_value=1, max_value=120, value=10)
    for i in range(waktu):
        temp = st.number_input(f"Menit ke-{i+1}: Suhu (°C)", value=25.0, step=0.1, key=f"temp_{i}")
        temps.append(temp)

if temps:
    f0 = calculate_f0(temps)
    f0_total = f0[-1]
    valid = check_minimum_holding_time(temps)
    status = "Lolos" if valid else "Tidak Lolos"

    st.info(f"📊 Data suhu valid ditemukan: {len(temps)} menit")
    st.success(f"✅ Nilai F₀ Total: {f0_total:.2f}")

    if valid:
        st.success("✅ Suhu ≥121.1°C tercapai minimal selama 3 menit")
    else:
        st.warning("⚠️ Suhu ≥121.1°C belum tercapai selama 3 menit")

    # Buat grafik
    fig, ax = plt.subplots()
    ax.plot(range(1, len(temps)+1), temps, label="Suhu (°C)", marker='o')
    ax.axhline(90, color='red', linestyle='--', label="Ambang F₀ (90°C)")
    ax.axhline(121.1, color='green', linestyle='--', label="Target BPOM (121.1°C)")
    ax.set_xlabel("Menit")
    ax.set_ylabel("Suhu (°C)")

    ax2 = ax.twinx()
    ax2.plot(range(1, len(f0)+1), f0, color='orange', label="F₀ Akumulatif", linestyle='--')
    ax2.set_ylabel("F₀")

    ax.legend(loc="center left")
    ax2.legend(loc="center right")

    st.pyplot(fig)

    # Simpan grafik ke file
    fig.savefig("grafik.png")

    # Buat PDF
    pdf = FPDF()
    pdf.set_title("Laporan Penghitungan F0")
    pdf.set_author("Data Proses")
    pdf.set_creator("Aplikasi Streamlit")
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Laporan Penghitungan F0", ln=True, align="C")
    pdf.ln(10)

    isi_laporan = (
        f"Produk: {nama_produk}\n"
        f"Tanggal Proses: {tanggal_proses.strftime('%d-%m-%Y')}\n"
        f"Operator: {nama_operator}\n"
        f"Alat Retort: {nama_alat}\n"
        f"Nilai F0: {f0_total:.2f}\n"
        f"Status Validasi: {status}"
    )
    pdf.multi_cell(0, 10, isi_laporan)
    pdf.ln(5)
    pdf.image("grafik.png", x=10, y=pdf.get_y(), w=180)

    # Simpan ke buffer dan tampilkan tombol unduh
    pdf_bytes = pdf.output(dest="S")
    buffer = BytesIO(pdf_bytes)

    st.download_button(
        label="💾 Unduh Laporan PDF",
        data=buffer,
        file_name="laporan_penghitungan_f0.pdf",
        mime="application/pdf"
    )

    st.success("Laporan berhasil dibuat dan siap diunduh.")
