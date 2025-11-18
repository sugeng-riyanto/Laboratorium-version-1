# models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import date
from sqlalchemy.orm import configure_mappers

db = SQLAlchemy()

# models.py

class Bahan(db.Model):
    __tablename__ = 'bahan'
    id = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(20), unique=True, nullable=False)
    nama_bahan = db.Column(db.String(100), nullable=False)
    kuantitas = db.Column(db.Float, default=0.0)  # Total stok awal (bisa bertambah saat input baru)
    satuan = db.Column(db.String(20), nullable=False)
    tgl_masuk = db.Column(db.Date, nullable=False)
    tgl_expired = db.Column(db.Date)
    status_expired = db.Column(db.String(20), default='belum expired')
    catatan = db.Column(db.Text)
    nama_lab = db.Column(db.String(20), nullable=False)

    # Kolom baru
    total_digunakan = db.Column(db.Float, default=0.0)  # Akumulasi yang pernah dipakai

    # Sisa tersedia dihitung dinamis
    @property
    def sisa_tersedia(self):
        return self.kuantitas - self.total_digunakan

    jadwals = db.relationship('JadwalPenggunaan', secondary='jadwal_bahan', back_populates='bahan')
    jadwal_bahan = db.relationship('JadwalBahan', back_populates='bahan_rel', overlaps="bahan,jadwals")


class Alat(db.Model):
    __tablename__ = 'alat'
    id = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(20), unique=True, nullable=False)
    nama_alat = db.Column(db.String(100), nullable=False)
    kuantitas = db.Column(db.Integer, default=1)  # Total alat yang dimiliki
    satuan = db.Column(db.String(20), nullable=False)
    tgl_masuk = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), default='baik')
    catatan = db.Column(db.Text)
    nama_lab = db.Column(db.String(20), nullable=False)

    # Kolom baru
    total_digunakan = db.Column(db.Integer, default=0)   # Akumulasi yang pernah digunakan
    sedang_dipakai = db.Column(db.Integer, default=0)    # Alat yang saat ini dipakai
    rusak = db.Column(db.Integer, default=0)             # Alat yang rusak

    # Tersedia dihitung dinamis
    @property
    def tersedia_baik(self):
        return self.kuantitas - self.sedang_dipakai - self.rusak

    jadwals = db.relationship('JadwalPenggunaan', secondary='jadwal_alat', back_populates='alat')
    kejadians = db.relationship('Kejadian', backref='alat', cascade='all, delete-orphan')
    jadwal_alat = db.relationship('JadwalAlat', back_populates='alat_rel', overlaps="alat,jadwals")


class JadwalPenggunaan(db.Model):
    __tablename__ = 'jadwal_penggunaan'
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.Date, nullable=False)
    nama_guru = db.Column(db.String(50), nullable=False)
    sesi = db.Column(db.String(20), nullable=False)
    kelas = db.Column(db.String(20), nullable=False)
    judul_praktikum = db.Column(db.String(100), nullable=False)
    jumlah_kelompok = db.Column(db.Integer, default=1)
    nama_lab = db.Column(db.String(20), nullable=False)

    # Status lama (untuk laporan)
    status_eksperimen = db.Column(db.String(20), default='belum selesai')

    # ✅ Status request baru (untuk pemantauan)
    status_request = db.Column(db.String(20), default='menunggu')  # menunggu, selesai, dibatalkan, tidak terlaksana
    catatan = db.Column(db.Text)

    # Laporan
    laporan_penggunaan = db.Column(db.Text)
    laporan_kegiatan = db.Column(db.Text)

    # Relasi ke item
    bahan = db.relationship('Bahan', secondary='jadwal_bahan', back_populates='jadwals')
    alat = db.relationship('Alat', secondary='jadwal_alat', back_populates='jadwals')

     # ✅ Tambahkan cascade di sini
    jadwal_bahan = db.relationship('JadwalBahan', back_populates='jadwal', cascade='all, delete-orphan', overlaps="bahan,jadwals")
    jadwal_alat = db.relationship('JadwalAlat', back_populates='jadwal', cascade='all, delete-orphan', overlaps="alat,jadwals")


class JadwalBahan(db.Model):
    __tablename__ = 'jadwal_bahan'
    id = db.Column(db.Integer, primary_key=True)
    jadwal_id = db.Column(db.Integer, db.ForeignKey('jadwal_penggunaan.id'), nullable=False)
    bahan_id = db.Column(db.Integer, db.ForeignKey('bahan.id'), nullable=False)
    kuantitas_digunakan = db.Column(db.Float, default=0.0)

    # Relasi balik — dengan overlaps
    jadwal = db.relationship('JadwalPenggunaan', back_populates='jadwal_bahan', overlaps="bahan,jadwals")
    bahan_rel = db.relationship('Bahan', back_populates='jadwal_bahan', overlaps="bahan,jadwals")


class JadwalAlat(db.Model):
    __tablename__ = 'jadwal_alat'
    id = db.Column(db.Integer, primary_key=True)
    jadwal_id = db.Column(db.Integer, db.ForeignKey('jadwal_penggunaan.id'), nullable=False)
    alat_id = db.Column(db.Integer, db.ForeignKey('alat.id'), nullable=False)
    kuantitas_digunakan = db.Column(db.Integer, default=1)

    # Relasi balik — dengan overlaps
    jadwal = db.relationship('JadwalPenggunaan', back_populates='jadwal_alat', overlaps="alat,jadwals")
    alat_rel = db.relationship('Alat', back_populates='jadwal_alat', overlaps="alat,jadwals")


class Kejadian(db.Model):
    __tablename__ = 'kejadian'
    id = db.Column(db.Integer, primary_key=True)
    tanggal_kejadian = db.Column(db.Date, nullable=False)
    nama_guru = db.Column(db.String(50), nullable=False)
    kelas = db.Column(db.String(20), nullable=False)
    sesi = db.Column(db.String(20), nullable=False)
    alat_id = db.Column(db.Integer, db.ForeignKey('alat.id'), nullable=False)
    kuantitas_rusak = db.Column(db.Integer, default=1)
    deskripsi = db.Column(db.Text)
    status = db.Column(db.String(20), default='belum ditangani')
    nama_lab = db.Column(db.String(20), nullable=False)


class BeritaAcara(db.Model):
    __tablename__ = 'berita_acara'
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.Date, nullable=False)
    jenis = db.Column(db.String(10), nullable=False)  # 'bahan' atau 'alat'
    item_id = db.Column(db.Integer, nullable=False)
    nama_item = db.Column(db.String(200), nullable=False)
    alasan = db.Column(db.String(100), nullable=False)  # 'Expired', 'Rusak', 'Hilang', 'Lainnya'
    keterangan = db.Column(db.Text)
    nama_petugas = db.Column(db.String(100), nullable=False)

    # Kolom untuk follow-up
    status_follow_up = db.Column(db.String(50), default='Belum Ditangani')
    kuantitas_tindakan = db.Column(db.Integer, default=0)
    tanggal_tindakan = db.Column(db.Date)
    catatan_tindakan = db.Column(db.Text)



# models.py - tambahkan di bawah model lainnya

# models.py

class Guru(db.Model):
    __tablename__ = 'guru'
    id = db.Column(db.Integer, primary_key=True)
    nama_guru = db.Column(db.String(50), unique=True, nullable=False)

class Kelas(db.Model):
    __tablename__ = 'kelas'
    id = db.Column(db.Integer, primary_key=True)
    nama_kelas = db.Column(db.String(20), unique=True, nullable=False)
    

# Pastikan semua relasi terdaftar
configure_mappers()