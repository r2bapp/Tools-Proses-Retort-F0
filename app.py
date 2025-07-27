import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import io
import datetime

# ===================== Fungsi Perhitungan F0 =====================
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

# ===================== Halaman Input Parameter =====================
def input_parameter_page():
    st.title("📋 Input Data Parameter Retort per Menit")

    if "df_parameter" not in st.session_state:
        st.session_state.df_parameter = pd.DataFrame(columns=["menit", "suhu", "tekanan"])

    with st.form("parameter_form", clear_on_submit=True):
        menit = st.number_input("Menit ke-", min_value=0, step=1)
        suhu = st.number_input("Suhu (°C)", min_value=0.0)
        tekanan = st.number_input("Tekanan (bar)", min_value=0.0)
        submitted = st.form_submit_button("➕ Tambahkan")

        if submitted:
            st.session_state.df_parameter.loc[len(st.session_state.df_parameter)] = {
                "menit": menit,
                "suhu": suhu,
                "tekanan": tekanan
            }

    if not st.session_state.df_parameter.empty:
        st.subheader("Data Parameter yang Dimasukkan")
        st.dataframe(st.session_state.df_parameter)

        if st.button("🗑️ Reset Data"):
            st.session_state.df_parameter = pd.DataFrame(columns=["menit", "suhu", "tekanan"])

# ===================== Halaman Hasil F0 dan Unduh PDF =====================
def hasil_f0_page():
    st.title("📈 Hasil dan Validasi F0")

    if "df_parameter" not in st.session_state or st.session_state.df_parameter.empty:
        st.warning("❗ Silakan input data parameter terlebih dahulu.")
        return

    df = st.session_state.df_parameter.copy()
    temps = df["suhu"].tolist()
    f0_cumsum = calculate_f0(temps)
    df["F0"] = f0_cumsum

    valid = check_minimum_holding_time(temps)
    status_validasi = "✅ Validasi BERHASIL" if valid else "❌ Validasi GAGAL"

    st.subheader("📌 Ringkasan Hasil F0")
    st.write(f"Total F0: **{f0_cumsum[-1]:.2f}**")
    st.write(f"Status: **{status_validasi}**")

    st.subheader("📊 Grafik Suhu & F0")
    fig, ax1 = plt.subplots()
    ax1.plot(df["menit"], df["suhu"], color="red", label="Suhu (°C)")
    ax1.set_xlabel("Menit")
    ax1.set_ylabel("Suhu (°C)", color="red")
    ax2 = ax1.twinx()
    ax2.plot(df["menit"], df["F0"], color="blue", label="F₀")
    ax2.set_ylabel("F₀", color="blue")
    st.pyplot(fig)

    st.subheader("✍️ Paraf / Tanda Tangan Manual")
    canvas_result = st.canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#ffffff",
        height=150,
        drawing_mode="freedraw",
        key="canvas_paraf"
    )

    st.subheader("📄 Unduh Laporan PDF")
    if st.button("Unduh PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(200, 10, "Laporan Proses Retort", ln=True, align="C")
        pdf.set_font("Arial", size=10)
        pdf.ln(5)

        pdf.cell(200, 10, f"Total F₀: {f0_cumsum[-1]:.2f}", ln=True)
        pdf.cell(200, 10, f"Status Validasi: {status_validasi}", ln=True)

        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(200, 10, "Data Parameter Proses per Menit", ln=True)
        pdf.set_font("Arial", size=9)
        for index, row in df.iterrows():
            pdf.cell(200, 8, f"Menit {row['menit']}: Suhu={row['suhu']}°C | Tekanan={row['tekanan']} bar | F₀={row['F0']:.2f}", ln=True)

        pdf.ln(5)
        pdf.set_font("Arial", size=8)
        pdf.cell(200, 10, "Proses retort dilakukan oleh Rumah Retort Bersama", ln=True, align="C")

        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        st.download_button(
            label="📄 Simpan PDF",
            data=pdf_output.getvalue(),
            file_name=f"Laporan_F0_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )

# ===================== Struktur Navigasi Halaman =====================
st.sidebar.title("🔧 Menu")
page = st.sidebar.radio("Pilih Halaman", ["Input Parameter", "Hasil & PDF"])

if page == "Input Parameter":
    input_parameter_page()
elif page == "Hasil & PDF":
    hasil_f0_page()
