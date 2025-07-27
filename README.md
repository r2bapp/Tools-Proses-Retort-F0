# 📦 Tools Proses Retort F₀ - Rumah Retort Bersama

Aplikasi berbasis **Streamlit Multipage** untuk menghitung dan memvalidasi proses sterilisasi **Retort** berdasarkan nilai **F₀** (lethality). Dikembangkan untuk mendukung pelaku UMKM pangan dalam memastikan keamanan proses tanpa cold chain.

---

## 🔧 Fitur Utama

✅ **Input Data Pelanggan & Retort**  
✅ **Input Data Per Menit (suhu, tekanan, keterangan)**  
✅ **Perhitungan Otomatis F₀**  
✅ **Validasi: Suhu ≥ 121.1°C selama ≥ 3 menit**  
✅ **Grafik Visualisasi Proses**  
✅ **Ringkasan dan Hasil F₀**  
✅ **Unduh PDF lengkap dengan watermark & struktur rapi**  
✅ **Sistem Login Sederhana (Bagoes, Iwan, Dimas)**  
✅ **Dukungan touchscreen untuk tanda tangan manual**  

---

## 🧮 Rumus Perhitungan F₀

```python
F₀ = Σ(10 ** ((T - 121.1) / z))
