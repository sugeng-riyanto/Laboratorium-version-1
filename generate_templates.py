# generate_templates.py
import pandas as pd
import os

# Buat folder static/templates jika belum ada
os.makedirs('static/templates', exist_ok=True)

# === TEMPLATE BAHAN ===
df_bahan = pd.DataFrame(columns=[
    'kode', 'nama_bahan', 'satuan', 'kuantitas', 'tgl_masuk',
    'tgl_expired', 'status_expired', 'catatan', 'nama_lab'
])
df_bahan.to_excel('static/templates/template_bahan.xlsx', index=False)

# === TEMPLATE ALAT ===
df_alat = pd.DataFrame(columns=[
    'kode', 'nama_alat', 'satuan', 'kuantitas', 'tgl_masuk',
    'status', 'catatan', 'nama_lab'
])
df_alat.to_excel('static/templates/template_alat.xlsx', index=False)

# === TEMPLATE KEJADIAN ===
df_kejadian = pd.DataFrame(columns=[
    'tanggal_kejadian', 'nama_guru', 'kelas', 'sesi', 'alat_id', 'kuantitas_rusak',
    'deskripsi', 'status', 'nama_lab'
])
df_kejadian.to_excel('static/templates/template_kejadian.xlsx', index=False)

print("✅ File template Excel berhasil dibuat di folder 'static/templates'")