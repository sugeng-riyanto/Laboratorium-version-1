# reset_db.py
import os
from datetime import date, datetime, timedelta
from app import app, db
from models import (
    Bahan, Alat, JadwalPenggunaan, JadwalBahan, JadwalAlat,
    Kejadian, BeritaAcara, Guru, Kelas
)

def create_seed_data():
    """Buat data contoh untuk development."""
    today = date.today()
    next_week = today + timedelta(days=7)

    # === GURU ===
    guru_list = [
        Guru(nama_guru='Mr Sugeng Riyanto'),
        Guru(nama_guru='Mr Aji Wahyu Budiyanto'),
        Guru(nama_guru='Mr Jia Bagus Ardianto'),
        Guru(nama_guru='Mr Bernadus Suharjo'),
        Guru(nama_guru='Ms Dian Pratiwi'),
        Guru(nama_guru='Mr Rudi Hartono'),
    ]
    for g in guru_list:
        db.session.add(g)

    # === KELAS ===
    kelas_list = [
        Kelas(nama_kelas='7A'), Kelas(nama_kelas='7B'),
        Kelas(nama_kelas='8A'), Kelas(nama_kelas='8B'),
        Kelas(nama_kelas='9A'), Kelas(nama_kelas='9B'),
        Kelas(nama_kelas='10'), Kelas(nama_kelas='11'),
        Kelas(nama_kelas='11A'), Kelas(nama_kelas='11B'),
        Kelas(nama_kelas='12'), Kelas(nama_kelas='12A'),
        Kelas(nama_kelas='12B'),
    ]
    for k in kelas_list:
        db.session.add(k)

    # === BAHAN CONTOH ===
    bahan_list = [
        Bahan(
            kode='B001',
            nama_bahan='Asam Klorida',
            satuan='mL',
            kuantitas=500.0,
            tgl_masuk=today,
            tgl_expired=today + timedelta(days=180),
            nama_lab='Kimia',
            total_digunakan=0.0
        ),
        Bahan(
            kode='B002',
            nama_bahan='NaOH',
            satuan='g',
            kuantitas=200.0,
            tgl_masuk=today,
            tgl_expired=today + timedelta(days=365),
            nama_lab='Kimia',
            total_digunakan=0.0
        ),
        Bahan(
            kode='B003',
            nama_bahan='Glukosa',
            satuan='g',
            kuantitas=100.0,
            tgl_masuk=today,
            tgl_expired=today + timedelta(days=90),
            nama_lab='Biologi',
            total_digunakan=0.0
        ),
        Bahan(
            kode='B004',
            nama_bahan='Air Suling',
            satuan='L',
            kuantitas=10.0,
            tgl_masuk=today,
            tgl_expired=None,
            nama_lab='Fisika',
            total_digunakan=0.0
        ),
    ]
    for b in bahan_list:
        db.session.add(b)

    # === ALAT CONTOH ===
    alat_list = [
        Alat(
            kode='A001',
            nama_alat='Mikroskop',
            satuan='unit',
            kuantitas=5,
            tgl_masuk=today,
            status='baik',
            nama_lab='Biologi',
            total_digunakan=0,
            sedang_dipakai=0,
            rusak=0
        ),
        Alat(
            kode='A002',
            nama_alat='Termometer',
            satuan='item',
            kuantitas=20,
            tgl_masuk=today,
            status='baik',
            nama_lab='Fisika',
            total_digunakan=0,
            sedang_dipakai=0,
            rusak=0
        ),
        Alat(
            kode='A003',
            nama_alat='Buret',
            satuan='item',
            kuantitas=10,
            tgl_masuk=today,
            status='baik',
            nama_lab='Kimia',
            total_digunakan=0,
            sedang_dipakai=0,
            rusak=0
        ),
        Alat(
            kode='A004',
            nama_alat='Pipet Tetes',
            satuan='item',
            kuantitas=50,
            tgl_masuk=today,
            status='baik',
            nama_lab='Kimia',
            total_digunakan=0,
            sedang_dipakai=0,
            rusak=0
        ),
    ]
    for a in alat_list:
        db.session.add(a)

    db.session.commit()  # Commit dulu agar ID tersedia

    # === JADWAL CONTOH ===
    jadwal = JadwalPenggunaan(
        tanggal=next_week,
        nama_guru='Mr Sugeng Riyanto',
        sesi='07:10 - 07:50',
        kelas='12A',
        judul_praktikum='Uji pH Larutan',
        jumlah_kelompok=4,
        nama_lab='Kimia',
        status_request='menunggu',
        catatan='Praktikum rutin'
    )
    db.session.add(jadwal)
    db.session.flush()  # Dapatkan ID jadwal

    # Relasi bahan & alat ke jadwal
    jb1 = JadwalBahan(jadwal_id=jadwal.id, bahan_id=1, kuantitas_digunakan=10.0)
    jb2 = JadwalBahan(jadwal_id=jadwal.id, bahan_id=2, kuantitas_digunakan=5.0)
    ja1 = JadwalAlat(jadwal_id=jadwal.id, alat_id=3, kuantitas_digunakan=4)
    ja2 = JadwalAlat(jadwal_id=jadwal.id, alat_id=4, kuantitas_digunakan=8)

    db.session.add_all([jb1, jb2, ja1, ja2])

    # === KEJADIAN CONTOH ===
    kejadian = Kejadian(
        tanggal_kejadian=today,
        nama_guru='Mr Aji Wahyu Budiyanto',
        kelas='11B',
        sesi='10:10 - 10:50',
        alat_id=1,
        kuantitas_rusak=1,
        deskripsi='Mikroskop jatuh saat dipindahkan.',
        status='belum ditangani',
        nama_lab='Biologi'
    )
    db.session.add(kejadian)

    # === BERITA ACARA CONTOH ===
    acara = BeritaAcara(
        tanggal=today,
        jenis='bahan',
        item_id=1,
        nama_item='Asam Klorida',
        alasan='Expired',
        keterangan='Stok lama sudah kadaluarsa.',
        nama_petugas='Admin Lab'
    )
    db.session.add(acara)

    db.session.commit()
    print("🌱 Seed data berhasil ditambahkan!")

if __name__ == '__main__':
    with app.app_context():
        # HAPUS FILE DATABASE LAMA
        if os.path.exists('lab.db'):
            os.remove('lab.db')
            print("🗑️ File lab.db lama dihapus.")

        # Buat ulang semua tabel
        db.create_all()
        print("✅ Database baru (lab.db) berhasil dibuat.")

        # Isi dengan data contoh
        create_seed_data()