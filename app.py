import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas

# ----------------------------
# KONSTANTA
# ----------------------------
F0_REFERENCE_TEMP = 121.1
Z_VALUE = 10
DB_PATH = "retort_data.db"

# ----------------------------
# INISIALISASI DATABASE
# ----------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pelanggan (
                    nama TEXT, tanggal TEXT, sesi TEXT, batch TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS data_per_minute (
                    menit INTEGER, suhu REAL, tekanan REAL, keterangan TEXT
                )''')
    conn.commit()
    conn.close()

# ----------------------------
# SIMPAN DATA
# ----------------------------
def simpan_data_pelanggan(nama, tanggal, sesi, batch):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO pelanggan VALUES (?, ?, ?, ?)", (nama, tanggal, sesi, batch))
    conn.commit()
    conn.close()

def simpan_data_per_menit(df):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for _, row in df.iterrows():
        c.execute("INSERT INTO data_per_minute VALUES (?, ?, ?, ?)", tuple(row))
    conn.commit()
    conn.close()

# ----------------------------
# FUNGSI HITUNG F0
# ----------------------------
def calculate_f0(df, T_ref=F0_REFERENCE_TEMP, z=Z_VALUE):
    temps = df['suhu'].tolist()
    f0_values = []
    for T in temps:
        if T < 90:
            f0_values.append(0)
        else:
            f0_values.append(10 ** ((T - T_ref) / z))
    df['f0'] = f0_values
    df['F0_kumulatif'] = pd.Series(f0_values).cumsum()
    total_f0 = df['F0_kumulatif'].iloc[-1]
    return df, total_f0

def check_minimum_holding_time(temps, min_temp=F0_REFERENCE_TEMP, min_duration=3):
    holding_minutes = 0
    for t in temps:
        if t >= min_temp:
            holding_minutes += 1
        else:
            holding_minutes = 0
        if holding_minutes >= min_duration:
            return True
    return False

# ----------------------------
# EXPORT PDF
# ----------------------------
def export_pdf(pelanggan_data, df):
    total_f0 = df['F0_kumulatif'].iloc[-1]
    valid = check_minimum_holding_time(df['suhu'].tolist())
    status_validasi = "✅ Validasi BERHASIL" if valid else "❌ Validasi GAGAL"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Laporan Proses Retort", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.ln(5)

    pdf.cell(200, 10, f"Nama: {pelanggan_data[0]}", ln=True)
    pdf.cell(200, 10, f"Tanggal: {pelanggan_data[1]}", ln=True)
    pdf.cell(200, 10, f"Sesi: {pelanggan_data[2]} - Batch: {pelanggan_data[3]}", ln=True)
    pdf.cell(200, 10, f"Total F₀: {total_f0:.2f}", ln=True)
    pdf.cell(200, 10, f"Status Validasi: {status_validasi}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(200, 10, "Data Parameter", ln=True)
    pdf.set_font("Arial", size=9)
    for index, row in df.iterrows():
        pdf.cell(200, 8, f"Menit {row['menit']}: Suhu={row['suhu']}°C | Tekanan={row['tekanan']} bar | F₀={row['f0']:.2f}", ln=True)

    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

# ----------------------------
# HALAMAN UTAMA
# ----------------------------
init_db()

st.title("📊 Aplikasi Perhitungan F₀ Retort")
st.markdown("Silakan input data pelanggan dan parameter proses retort di bawah ini.")

with st.form("form_pelanggan"):
    nama = st.text_input("Nama Pelanggan")
    tanggal = st.date_input("Tanggal", datetime.date.today())
    sesi = st.selectbox("Sesi", ["Pagi", "Siang", "Sore", "Malam"])
    batch = st.text_input("Batch Produk")
    submitted = st.form_submit_button("Simpan Data Pelanggan")
    if submitted:
        simpan_data_pelanggan(nama, str(tanggal), sesi, batch)
        st.success("✅ Data pelanggan disimpan.")

st.markdown("---")
st.markdown("### Input Parameter Per Menit")

df_input = pd.DataFrame({
    "menit": list(range(1, 11)),
    "suhu": [0]*10,
    "tekanan": [0]*10,
    "keterangan": [""]*10
})

edited_df = st.data_editor(df_input, num_rows="dynamic", use_container_width=True)

if st.button("💾 Simpan & Hitung F₀"):
    simpan_data_per_menit(edited_df)
    df_hasil, total_f0 = calculate_f0(edited_df)

    st.markdown("### 🔍 Hasil Perhitungan F₀")
    st.dataframe(df_hasil, use_container_width=True)
    st.metric("Total F₀", f"{total_f0:.2f}")

    validasi = check_minimum_holding_time(df_hasil['suhu'].tolist())
    if validasi:
        st.success("✅ Validasi SUHU berhasil: Suhu ≥121.1°C selama ≥3 menit")
    else:
        st.error("❌ Validasi GAGAL: Suhu belum memenuhi syarat keamanan")

    st.markdown("---")
    pdf_file = export_pdf((nama, str(tanggal), sesi, batch), df_hasil)
    st.download_button(
        label="📥 Unduh Laporan PDF",
        data=pdf_file,
        file_name=f"Laporan_Retort_{nama}_{tanggal}.pdf",
        mime="application/pdf"
    )
