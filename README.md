# Tools Retort R2B

Aplikasi pencatatan proses retort dengan perhitungan otomatis nilai F₀, dilengkapi fitur input data pelanggan, parameter suhu dan tekanan tiap menit, serta ekspor laporan PDF lengkap dengan watermark "Diproses oleh Rumah Retort Bersama".

## Cara Menjalankan

1. Install dependensi:
```bash
pip install -r requirements.txt
```

2. Jalankan aplikasi:
```bash
streamlit run app.py
```

## Fitur
- Login pengguna (iwan, bagoes, dimas)
- Input data pelanggan
- Input proses: waktu venting, cut, holding, cooling
- Data produk & basket
- Input suhu & tekanan per menit
- Perhitungan F0 otomatis
- Ekspor laporan PDF

