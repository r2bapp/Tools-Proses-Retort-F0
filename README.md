# 🔥 Retort F0 Tools - Rumah Retort Bersama (R2B)

Aplikasi berbasis **Streamlit** untuk membantu dokumentasi proses **retort** secara manual dan menghitung nilai **F0** secara otomatis, disertai visualisasi dan ekspor laporan. Dirancang khusus untuk UMKM pengolahan pangan steril komersial.

---

## ✨ Fitur Utama

✅ Input Data Pelanggan dan Informasi Proses  
✅ Durasi Proses: Venting, CUT, Holding, Cooling  
✅ Input Data Produk dalam Basket (1–3)  
✅ Pantauan Proses per Menit: Waktu, Suhu, Tekanan  
✅ Perhitungan Otomatis Nilai F0  
✅ Dashboard Visualisasi F0 (Grafik & Keterangan)  
✅ Ekspor ke PDF & CSV  
✅ Upload Logo R2B & Tampilan Kustomisasi  
✅ Siap Upload ke Google Drive *(opsional fitur)*

---

## 📸 Tampilan Aplikasi

![Logo R2B](./R2B.png)

---

## ⚙️ Teknologi

- Python 3.x
- [Streamlit](https://streamlit.io/)
- SQLite (database lokal)
- Pandas, Matplotlib
- FPDF (ekspor PDF)
- Pillow (logo image handling)

---

## 🧮 Tentang F0

> Nilai **F0** adalah indikator keberhasilan proses sterilisasi termal.
>
> **Rumus:**
>
> ```
> F0 = ∆t × Σ [10^((T - Tb)/Z)]
> ```
>
> - ∆t = interval waktu (menit), biasanya 1
> - T = suhu aktual saat proses (°C)
> - Tb = suhu referensi (121.1°C)
> - Z = nilai perubahan suhu untuk 1 log reduksi (default 10°C)

---

## 📦 Instalasi Lokal

```bash
# 1. Clone repository
git clone https://github.com/username/retort-f0-tools.git
cd retort-f0-tools

# 2. Instal dependensi
pip install -r requirements.txt

# 3. Jalankan aplikasi
streamlit run app.py
