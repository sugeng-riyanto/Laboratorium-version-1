# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask import jsonify
from flask import jsonify, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pandas as pd
import os
import io
import threading
from datetime import datetime, timedelta, date
import random
import string
from models import db, Bahan, Alat, Kejadian, JadwalPenggunaan, JadwalBahan, JadwalAlat, BeritaAcara, Guru, Kelas
from sqlalchemy import func
import time
import zoneinfo
import calendar
from flask import send_file
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors


from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape


from flask import jsonify
from flask_login import login_required
from sqlalchemy import func
#pip install --upgrade --force-reinstall reportlab
# --- KONSTANTA ---
SATUAN_BAHAN = [
    '-','mol/dm³', '% (v/v)', 'g', 'cm', 'mL', 'cm³', 'tetes', 'µL', 'Ω', 'V',
    'kg', 's', 'mA', 'A', 'm', 'mm', '°C', 'J', 'kJ', 'g', 'nm',
    'absorbansi', 'perbesaran', 'sel per mm³', 'sel per mL', 'kPa', 'atm', 'mmH₂O'
]
SATUAN_ALAT = [
    'item','g', 'cm³', 'mL', 'µL', '°C', '(tidak bersatuan)', 'kali', 'mm', 'cm', 's',
    'A', 'V', 'Ω', '×g', 'nm', 'sel/mL', 'm/s', 'kPa', 'J', 'unit','-'
]

# --- INISIALISASI FLASK ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lab.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
favicon_path = os.path.join(app.static_folder, 'uploads', 'favicon.ico')
logo_path = os.path.join(app.static_folder, 'uploads', 'logo.png')



# --- USER MODEL ---
class User(UserMixin):
    def __init__(self, id):
        self.id = id
users = {"admin": User("admin")}

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

# --- CONTEXT PROCESSORS ---
@app.context_processor
def inject_now():
    jakarta_tz = zoneinfo.ZoneInfo("Asia/Jakarta")
    return {'current_year': datetime.now(jakarta_tz).year}

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# --- FUNGSI PEMBANTU ---
def generate_captcha():
    chars = string.ascii_uppercase + string.digits
    captcha = ''.join(random.choice(chars) for _ in range(5))
    session['captcha'] = captcha
    return captcha

def delete_file_after_delay(filepath, delay=5):
    def _delete():
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"❌ Gagal menghapus file {filepath}: {e}")
    timer = threading.Timer(delay, _delete)
    timer.start()

def parse_sesi_start(sesi_str):
    start_time_str = sesi_str.split(' - ')[0]
    return datetime.strptime(start_time_str, '%H:%M').time()

def parse_sesi_end(sesi_str):
    end_time_str = sesi_str.split(' - ')[1]
    return datetime.strptime(end_time_str, '%H:%M').time()

def restore_stock(jadwal):
    """Kembalikan stok alat dan bahan ke semula."""
    for ja in jadwal.jadwal_alat:
        alat = Alat.query.get(ja.alat_id)
        if alat:
            alat.sedang_dipakai -= ja.kuantitas_digunakan
    for jb in jadwal.jadwal_bahan:
        bahan = Bahan.query.get(jb.bahan_id)
        if bahan:
            bahan.total_digunakan -= jb.kuantitas_digunakan

# --- FUNGSI OTOMATISASI ---
def check_and_update_expired_bahan():
    today = datetime.now().date()
    expired_bahan = Bahan.query.filter(
        Bahan.tgl_expired.isnot(None),
        Bahan.tgl_expired <= today,
        Bahan.status_expired == 'belum expired'
    ).all()
    for b in expired_bahan:
        b.status_expired = 'expired'
        acara = BeritaAcara(
            tanggal=today,
            jenis='bahan',
            item_id=b.id,
            nama_item=b.nama_bahan,
            alasan='Expired',
            keterangan=f'Bahan {b.nama_bahan} (Kode: {b.kode}) telah melewati tanggal kadaluarsa ({b.tgl_expired}).',
            nama_petugas='Sistem Otomatis'
        )
        db.session.add(acara)
    if expired_bahan:
        db.session.commit()

# --- ROUTE UTAMA ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_input_captcha = request.form['captcha'].strip().upper()
        correct_captcha = session.get('captcha', '')
        if username == 'admin' and password == 'password123' and user_input_captcha == correct_captcha:
            login_user(users['admin'])
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username, password, atau CAPTCHA salah.', 'danger')
    captcha_text = generate_captcha()
    return render_template('login.html', captcha_text=captcha_text)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin_index():
    return render_template('admin/index.html')


# app.py

import os
from flask import send_from_directory

# === KONFIGURASI UPLOAD FOLDER ===
# Pastikan UPLOAD_FOLDER diatur dengan benar di config Anda
# Contoh: app.config['UPLOAD_FOLDER'] = 'static/uploads'


# app.py

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    """Halaman pengaturan favicon & logo."""
    if request.method == 'POST':
        try:
            # === UPLOAD FAVICON ===
            favicon = request.files.get('favicon')
            if favicon and favicon.filename.endswith(('.ico', '.png', '.jpg', '.jpeg')):
                # ✅ Simpan ke static/uploads/favicon.ico
                favicon_path = os.path.join(app.static_folder, 'uploads', 'favicon.ico')
                # Hapus file lama jika ada
                if os.path.exists(favicon_path):
                    os.remove(favicon_path)
                favicon.save(favicon_path)
                flash('Favicon berhasil diperbarui!', 'success')
            elif favicon:
                flash('File favicon harus berekstensi .ico, .png, .jpg, atau .jpeg', 'danger')

            # === UPLOAD LOGO ===
            logo = request.files.get('logo')
            if logo and logo.filename.endswith(('.png', '.jpg', '.jpeg')):
                # ✅ Simpan ke static/uploads/logo.png
                logo_path = os.path.join(app.static_folder, 'uploads', 'logo.png')
                # Hapus file lama jika ada
                if os.path.exists(logo_path):
                    os.remove(logo_path)
                logo.save(logo_path)
                flash('Logo berhasil diperbarui!', 'success')
            elif logo:
                flash('File logo harus berekstensi .png, .jpg, atau .jpeg', 'danger')

        except Exception as e:
            flash(f'Error upload: {str(e)}', 'danger')

    return render_template('admin/settings.html')

# --- DASHBOARD UTAMA ---
@app.route('/')
@login_required
def dashboard():
    start_date_str = request.args.get('start_date')
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = datetime.now().date()
    else:
        start_date = datetime.now().date()
    start_of_week = start_date - timedelta(days=start_date.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat']
    dates = [(start_of_week + timedelta(days=i)).strftime('%d %b') for i in range(5)]
    day_date_pairs = list(zip(days, dates))
    times = [
        '07:10 - 07:50', '07:50 - 08:30', '08:30 - 09:10', '09:10 - 09:50',
        '10:10 - 10:50', '10:50 - 11:30', '11:30 - 12:10', '12:50 - 13:30',
        '13:30 - 14:10', '14:10 - 14:50', '14:50 - 15:30'
    ]
    labs = ['Fisika', 'Kimia', 'Biologi']
    schedule_grids = {}
    for lab in labs:
        jadwals = JadwalPenggunaan.query.filter(
            JadwalPenggunaan.tanggal.between(start_of_week, end_of_week),
            JadwalPenggunaan.nama_lab == lab
        ).all()
        grid = {t: {d: [] for d in days} for t in times}
        for j in jadwals:
            weekday = j.tanggal.weekday()
            if 0 <= weekday <= 4:
                day_name = days[weekday]
                if j.sesi in times:
                    grid[j.sesi][day_name].append(j)
        schedule_grids[lab] = grid
    prev_week = start_of_week - timedelta(days=7)
    next_week = start_of_week + timedelta(days=7)
    return render_template('dashboard.html',
                           day_date_pairs=day_date_pairs,
                           times=times,
                           schedule_grids=schedule_grids,
                           current_start_date=start_of_week.strftime('%Y-%m-%d'),
                           prev_week_date=prev_week.strftime('%Y-%m-%d'),
                           next_week_date=next_week.strftime('%Y-%m-%d'))


# app.py

@app.route('/download/template/<tipe>')
@login_required
def download_template(tipe):
    """Serve file template Excel untuk download."""
    valid_tipe = ['bahan', 'alat', 'kejadian']
    if tipe not in valid_tipe:
        flash('Tipe template tidak dikenali.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    filename = f"template_{tipe}.xlsx"
    filepath = os.path.join(app.root_path, 'static', 'templates', filename)

    if not os.path.exists(filepath):
        flash(f'File template {filename} tidak ditemukan.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    return send_from_directory(
        os.path.join(app.root_path, 'static', 'templates'),
        filename,
        as_attachment=True,
        download_name=filename
    )

# --- ANALYTICS DASHBOARD ---
@app.route('/analytics')
@login_required
def analytics_dashboard():
    try:
        bahan_list = Bahan.query.all()
        alat_list = Alat.query.all()
        kejadian_list = Kejadian.query.all()
        jadwal_list = JadwalPenggunaan.query.all()

        # Hitung countdown bahan
        for b in bahan_list:
            b.countdown_str = None
            b.countdown_seconds = 0
            if b.tgl_expired and b.status_expired == 'belum expired':
                expiry_datetime = datetime.combine(b.tgl_expired, datetime.min.time())
                now_datetime = datetime.now()
                diff = expiry_datetime - now_datetime
                if diff.total_seconds() > 0:
                    b.countdown_str = (now_datetime + diff).strftime('%Y-%m-%d %H:%M:%S')
                    b.countdown_seconds = int(diff.total_seconds())
                else:
                    b.status_expired = 'expired'
                    acara = BeritaAcara(
                        tanggal=datetime.now().date(),
                        jenis='bahan',
                        item_id=b.id,
                        nama_item=b.nama_bahan,
                        alasan='Expired',
                        keterangan=f'Bahan {b.nama_bahan} (Kode: {b.kode}) telah melewati tanggal kadaluarsa ({b.tgl_expired}).',
                        nama_petugas='Sistem Otomatis'
                    )
                    db.session.add(acara)

        db.session.commit()

        return render_template('analytics/dashboard.html',
            bahan_list=bahan_list,
            alat_list=alat_list,
            kejadian_list=kejadian_list,
            jadwal_list=jadwal_list,
            total_bahan=len(bahan_list),
            expired_bahan=Bahan.query.filter_by(status_expired='expired').count(),
            total_alat=len(alat_list),
            rusak_alat=Alat.query.filter_by(status='rusak').count(),
            total_kejadian=len(kejadian_list),
            total_jadwal=len(jadwal_list))
    except Exception as e:
        db.session.rollback()
        flash(f'Error memuat dashboard analitik: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))




@app.route('/api/analytics/data')
@login_required
def analytics_data():
    """
    API endpoint untuk menyediakan data JSON untuk semua grafik di dashboard analitik.
    """
    try:
        # === BAHAN ===
        bahan_per_lab = db.session.query(
            Bahan.nama_lab,
            func.count(Bahan.id).label('count')
        ).group_by(Bahan.nama_lab).all()

        expired_bahan_count = Bahan.query.filter_by(status_expired='expired').count()
        total_bahan_count = Bahan.query.count()

        # === ALAT ===
        alat_per_lab = db.session.query(
            Alat.nama_lab,
            func.count(Alat.id).label('count')
        ).group_by(Alat.nama_lab).all()

        rusak_alat_count = Alat.query.filter_by(status='rusak').count()
        total_alat_count = Alat.query.count()

        # === KEJADIAN ===
        # Diasumsikan format tanggal di database adalah DATE
        kejadian_per_bulan = db.session.query(
            func.strftime('%Y-%m', Kejadian.tanggal_kejadian).label('bulan'),
            func.count(Kejadian.id).label('count')
        ).group_by(func.strftime('%Y-%m', Kejadian.tanggal_kejadian)).order_by('bulan').all()

        kejadian_per_lab = db.session.query(
            Kejadian.nama_lab,
            func.count(Kejadian.id).label('count')
        ).group_by(Kejadian.nama_lab).all()

        # === JADWAL PENGGUNAAN ===
        jadwal_per_lab = db.session.query(
            JadwalPenggunaan.nama_lab,
            func.count(JadwalPenggunaan.id).label('count')
        ).group_by(JadwalPenggunaan.nama_lab).all()

        # === HISTOGRAM TAMBAHAN BERDASARKAN DATA DATABASE ===

        # 1. Histogram: Kelas vs Jumlah Eksperimen (Jadwal Penggunaan)
        histogram_kelas = db.session.query(
            JadwalPenggunaan.kelas.label('label'),
            func.count(JadwalPenggunaan.id).label('count')
        ).group_by(JadwalPenggunaan.kelas).all()

        # 2. Histogram: Nama Guru vs Jumlah Eksperimen (Jadwal Penggunaan)
        histogram_guru = db.session.query(
            JadwalPenggunaan.nama_guru.label('label'),
            func.count(JadwalPenggunaan.id).label('count')
        ).group_by(JadwalPenggunaan.nama_guru).all()

        # 3. Histogram: Nama Lab vs Bahan Expired
        histogram_lab_expired = db.session.query(
            Bahan.nama_lab.label('label'),
            func.count(Bahan.id).label('count')
        ).filter_by(status_expired='expired').group_by(Bahan.nama_lab).all()

        # 4. Histogram: Nama Lab vs Status Alat (Stacked Bar)
        # Perbaikan: Hitung 'baik' secara manual dengan ekspresi kolom
        histogram_lab_alat = db.session.query(
            Alat.nama_lab.label('lab'),
            # Baik = kuantitas - rusak - sedang_dipakai
            func.sum(Alat.kuantitas - Alat.rusak - Alat.sedang_dipakai).label('baik'),
            func.sum(Alat.rusak).label('rusak'),
            func.sum(Alat.sedang_dipakai).label('digunakan')
        ).group_by(Alat.nama_lab).all()

        # === PIECHART BERDASARKAN DATA DATABASE ===

        # (Menggunakan data yang sudah dihitung di atas)
        piechart_bahan = bahan_per_lab
        piechart_alat = alat_per_lab

        # === DATA UNTUK PERBANDINGAN.HTML ===

        # --- Hitung data untuk 3 bulan terakhir ---
        today = date.today()
        bulan_ini = today.replace(day=1)
        bulan_lalu = (bulan_ini - timedelta(days=1)).replace(day=1)
        dua_bulan_lalu = (bulan_lalu - timedelta(days=1)).replace(day=1)

        # Format nama bulan
        nama_bulan_list = [calendar.month_name[i] for i in range(1, 13)]
        labels = [
            nama_bulan_list[dua_bulan_lalu.month - 1],
            nama_bulan_list[bulan_lalu.month - 1],
            nama_bulan_list[bulan_ini.month - 1]
        ]

        # --- Hitung data untuk setiap bulan ---
        def hitung_data_per_bulan(tgl_awal_bulan):
            akhir_bulan = (tgl_awal_bulan + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            total_jadwal = JadwalPenggunaan.query.filter(
                JadwalPenggunaan.tanggal.between(tgl_awal_bulan, akhir_bulan)
            ).count()
            
            total_kejadian = Kejadian.query.filter(
                Kejadian.tanggal_kejadian.between(tgl_awal_bulan, akhir_bulan)
            ).count()
            
            expired_bahan = Bahan.query.filter(
                Bahan.tgl_expired.between(tgl_awal_bulan, akhir_bulan),
                Bahan.status_expired == 'expired'
            ).count()
            
            rusak_alat = Alat.query.filter(
                Alat.tgl_masuk.between(tgl_awal_bulan, akhir_bulan),
                Alat.status == 'rusak'
            ).count()
            
            return {
                'total_jadwal': total_jadwal,
                'total_kejadian': total_kejadian,
                'expired_bahan': expired_bahan,
                'rusak_alat': rusak_alat
            }

        data_dua_bulan_lalu = hitung_data_per_bulan(dua_bulan_lalu)
        data_bulan_lalu = hitung_data_per_bulan(bulan_lalu)
        data_bulan_ini = hitung_data_per_bulan(bulan_ini)

        # --- Format data untuk grafik perbandingan ---
        jadwal_data = [
            data_dua_bulan_lalu['total_jadwal'],
            data_bulan_lalu['total_jadwal'],
            data_bulan_ini['total_jadwal']
        ]
        kejadian_data = [
            data_dua_bulan_lalu['total_kejadian'],
            data_bulan_lalu['total_kejadian'],
            data_bulan_ini['total_kejadian']
        ]
        expired_data = [
            data_dua_bulan_lalu['expired_bahan'],
            data_bulan_lalu['expired_bahan'],
            data_bulan_ini['expired_bahan']
        ]
        rusak_data = [
            data_dua_bulan_lalu['rusak_alat'],
            data_bulan_lalu['rusak_alat'],
            data_bulan_ini['rusak_alat']
        ]

        # --- Format data untuk line chart tren kejadian (12 bulan terakhir) ---
        line_labels = []
        line_data = []
        for i in range(12):
            # Hitung bulan mundur dari bulan ini
            bulan_tren = (today.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
            nama_bulan_tren = nama_bulan_list[bulan_tren.month - 1]
            line_labels.insert(0, nama_bulan_tren[:3]) # Hanya 3 huruf pertama, e.g., 'Okt'
            
            akhir_bulan_tren = (bulan_tren + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            count_tren = Kejadian.query.filter(
                Kejadian.tanggal_kejadian.between(bulan_tren, akhir_bulan_tren)
            ).count()
            line_data.insert(0, count_tren)

        # --- Format data untuk doughnut chart distribusi kejadian per lab (bulan ini vs 1 bulan lalu) ---
        # Kejadian per lab bulan ini
        kejadian_bulan_ini_per_lab = db.session.query(
            Kejadian.nama_lab,
            func.count(Kejadian.id).label('count')
        ).filter(
            Kejadian.tanggal_kejadian.between(bulan_ini, (bulan_ini + timedelta(days=32)).replace(day=1) - timedelta(days=1))
        ).group_by(Kejadian.nama_lab).all()
        
        # Kejadian per lab 1 bulan lalu
        kejadian_bulan_lalu_per_lab = db.session.query(
            Kejadian.nama_lab,
            func.count(Kejadian.id).label('count')
        ).filter(
            Kejadian.tanggal_kejadian.between(bulan_lalu, (bulan_lalu + timedelta(days=32)).replace(day=1) - timedelta(days=1))
        ).group_by(Kejadian.nama_lab).all()

        # Gabungkan lab dari kedua bulan
        semua_lab_set = set([k[0] for k in kejadian_bulan_ini_per_lab]).union(set([k[0] for k in kejadian_bulan_lalu_per_lab]))
        doughnut_labels = list(semua_lab_set)
        
        # Mapping lab ke jumlah untuk bulan ini dan bulan lalu
        map_bulan_ini = {k[0]: k[1] for k in kejadian_bulan_ini_per_lab}
        map_bulan_lalu = {k[0]: k[1] for k in kejadian_bulan_lalu_per_lab}
        
        doughnut_data_bulan_ini = [map_bulan_ini.get(lab, 0) for lab in doughnut_labels]
        doughnut_data_bulan_lalu = [map_bulan_lalu.get(lab, 0) for lab in doughnut_labels]

        # === FORMAT DATA UNTUK JSON ===
        def format_simple_chart(query_result):
            """Helper untuk format hasil query ke dict labels & data."""
            return {
                'labels': [getattr(item, 'label', None) or item[0] for item in query_result],
                'data': [getattr(item, 'count', None) or item[1] for item in query_result]
            }

        def format_lab_chart(query_result):
            """Helper untuk format hasil query lab ke dict lab & count."""
            return [{'lab': item[0], 'count': item[1]} for item in query_result]

        # === KIRIM DATA DALAM FORMAT JSON ===
        return jsonify({
            'bahan': {
                'per_lab': format_lab_chart(bahan_per_lab),
                'total': total_bahan_count,
                'expired': expired_bahan_count
            },
            'alat': {
                'per_lab': format_lab_chart(alat_per_lab),
                'total': total_alat_count,
                'rusak': rusak_alat_count
            },
            'kejadian': {
                'per_bulan': [{'bulan': item[0], 'count': item[1]} for item in kejadian_per_bulan],
                'per_lab': format_lab_chart(kejadian_per_lab)
            },
            'jadwal': {
                'per_lab': format_lab_chart(jadwal_per_lab)
            },
            'histogram': {
                'kelas': format_simple_chart(histogram_kelas),
                'guru': format_simple_chart(histogram_guru),
                'lab_expired': format_simple_chart(histogram_lab_expired),
                'lab_alat': {
                    'labels': [item.lab for item in histogram_lab_alat],
                    'baik': [int(item.baik or 0) for item in histogram_lab_alat], # Pastikan integer
                    'rusak': [int(item.rusak or 0) for item in histogram_lab_alat],
                    'digunakan': [int(item.digunakan or 0) for item in histogram_lab_alat],
                }
            },
            'piechart': {
                'bahan': format_lab_chart(piechart_bahan),
                'alat': format_lab_chart(piechart_alat)
            },
            # === DATA UNTUK PERBANDINGAN.HTML ===
            'labels': labels,
            'jadwal_data': jadwal_data,
            'kejadian_data': kejadian_data,
            'expired_data': expired_data,
            'rusak_data': rusak_data,
            'line_labels': line_labels,
            'line_data': line_data,
            'doughnut_labels': doughnut_labels,
            'doughnut_data_bulan_ini': doughnut_data_bulan_ini,
            'doughnut_data_bulan_lalu': doughnut_data_bulan_lalu
        })

    except Exception as e:
        # Tangani error dan kirim pesan kesalahan
        app.logger.error(f"Error in /api/analytics/data: {e}") # Gunakan logger jika tersedia
        # Atau print ke console untuk debugging
        print(f"Error in /api/analytics/data: {e}")
        # Kembalikan error JSON agar frontend bisa menanganinya
        return jsonify({'error': 'Failed to fetch analytics data'}), 500


# --- CRUD BAHAN ---
@app.route('/admin/bahan')
@app.route('/admin/bahan/<lab>')
@login_required
def bahan_list(lab=None):
    valid_labs = ['Fisika', 'Kimia', 'Biologi']
    if lab and lab in valid_labs:
        bahan = Bahan.query.filter_by(nama_lab=lab).all()
    else:
        lab = "Semua"
        bahan = Bahan.query.all()
    return render_template('admin/bahan/list.html', bahan=bahan, lab=lab)


@app.route('/admin/bahan/create/<lab>', methods=['GET', 'POST'])
@login_required
def bahan_create(lab):
    if request.method == 'POST':
        try:
            satuan = request.form['satuan']
            if satuan == 'custom':
                satuan_manual = request.form.get('satuan_manual', '').strip()
                if not satuan_manual:
                    flash('Satuan manual tidak boleh kosong!', 'danger')
                    return render_template('admin/bahan/create_bahan.html', title=f"Tambah Bahan ({lab})", lab=lab, satuan_bahan=SATUAN_BAHAN)
                satuan = satuan_manual
            b = Bahan(
                kode=request.form['kode'],
                nama_bahan=request.form['nama_bahan'],
                satuan=satuan,
                kuantitas=float(request.form['kuantitas']),
                tgl_masuk=datetime.strptime(request.form['tgl_masuk'], '%Y-%m-%d').date(),
                tgl_expired=datetime.strptime(request.form['tgl_expired'], '%Y-%m-%d').date() if request.form.get('tgl_expired') else None,
                status_expired=request.form.get('status_expired', 'belum expired'),
                catatan=request.form.get('catatan', ''),
                nama_lab=lab
            )
            db.session.add(b)
            db.session.commit()
            flash(f'Bahan {lab} berhasil ditambahkan!', 'success')
            return redirect(url_for('bahan_list', lab=lab))
        except Exception as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
    return render_template('admin/bahan/create_bahan.html', title=f"Tambah Bahan ({lab})", lab=lab, satuan_bahan=SATUAN_BAHAN)


@app.route('/admin/bahan/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def bahan_edit(id):
    b = Bahan.query.get_or_404(id)
    lab = b.nama_lab
    if request.method == 'POST':
        try:
            b.kode = request.form['kode']
            b.nama_bahan = request.form['nama_bahan']
            b.kuantitas = float(request.form['kuantitas'])
            satuan = request.form['satuan']
            if satuan == 'custom':
                satuan_manual = request.form.get('satuan_manual', '').strip()
                if not satuan_manual:
                    flash('Satuan manual tidak boleh kosong!', 'danger')
                    return render_template('admin/bahan/edit_bahan.html', title="Edit Bahan", bahan=b, satuan_bahan=SATUAN_BAHAN)
                satuan = satuan_manual
            b.satuan = satuan
            b.tgl_masuk = datetime.strptime(request.form['tgl_masuk'], '%Y-%m-%d').date()
            b.tgl_expired = datetime.strptime(request.form['tgl_expired'], '%Y-%m-%d').date() if request.form.get('tgl_expired') else None
            b.status_expired = request.form.get('status_expired', 'belum expired')
            b.catatan = request.form.get('catatan', '')
            db.session.commit()
            flash('Bahan berhasil diperbarui!', 'success')
            return redirect(url_for('bahan_list', lab=lab))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    return render_template('admin/bahan/edit_bahan.html', title="Edit Bahan", bahan=b, satuan_bahan=SATUAN_BAHAN)




@app.route('/admin/bahan/delete/<int:id>', methods=['POST'])
@login_required
def bahan_delete(id):
    b = Bahan.query.get_or_404(id)
    lab = b.nama_lab
    db.session.delete(b)
    db.session.commit()
    flash('Bahan berhasil dihapus!', 'success')
    return redirect(url_for('bahan_list', lab=lab))

# === FUNGSI PEMBANTU ===

def delete_file_after_delay(filepath, delay=5.0):
    """Hapus file setelah delay detik."""
    import threading
    import time
    def _delete():
        time.sleep(delay)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"🗑️ File {filepath} berhasil dihapus setelah {delay} detik.")
            except Exception as e:
                print(f"❌ Gagal menghapus file {filepath}: {e}")
    timer = threading.Timer(delay, _delete)
    timer.daemon = True
    timer.start()

# === ROUTE UPLOAD EXCEL ===

# app.py

@app.route('/admin/bahan/upload', methods=['GET', 'POST'])
@login_required
def bahan_upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.xlsx'):
            flash('File Excel (.xlsx) diperlukan.', 'danger')
            return redirect(request.url)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        try:
            df = pd.read_excel(filepath)

            # ✅ Validasi kolom wajib
            required_columns = ['kode', 'nama_bahan', 'satuan', 'kuantitas', 'tgl_masuk']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                flash(f'File tidak memiliki kolom wajib: {", ".join(missing_columns)}', 'danger')
                raise ValueError("Kolom wajib tidak lengkap")

            for _, row in df.iterrows():
                # ✅ Validasi dan ambil data
                kode = str(row['kode']).strip()
                nama_bahan = str(row['nama_bahan']).strip()
                satuan = str(row['satuan']).strip() if 'satuan' in row and pd.notna(row['satuan']) and str(row['satuan']).strip() != '' else 'pcs'
                kuantitas = float(row['kuantitas'])
                tgl_masuk = pd.to_datetime(row['tgl_masuk']).date()
                tgl_expired = pd.to_datetime(row['tgl_expired']).date() if 'tgl_expired' in row and pd.notna(row['tgl_expired']) else None
                status_expired = str(row['status_expired']).strip() if 'status_expired' in row else 'belum expired'
                catatan = str(row['catatan']).strip() if 'catatan' in row else ''
                nama_lab = str(row['nama_lab']).strip() if 'nama_lab' in row else 'Fisika'

                # ✅ Validasi data dasar
                if not kode or not nama_bahan:
                    flash(f'Baris {_+1}: Kode dan Nama Bahan wajib diisi.', 'danger')
                    continue
                if kuantitas <= 0:
                    flash(f'Baris {_+1}: Kuantitas harus lebih dari 0.', 'danger')
                    continue

                # ✅ Buat objek Bahan
                b = Bahan(
                    kode=kode,
                    nama_bahan=nama_bahan,
                    satuan=satuan,
                    kuantitas=kuantitas,
                    tgl_masuk=tgl_masuk,
                    tgl_expired=tgl_expired,
                    status_expired=status_expired,
                    catatan=catatan,
                    nama_lab=nama_lab,
                    total_digunakan=0.0
                )
                db.session.add(b)
            db.session.commit()
            flash('Data bahan berhasil diimpor!', 'success')
            delete_file_after_delay(filepath, delay=5.0)
            return redirect(url_for('bahan_list'))
        except ValueError as ve:
            db.session.rollback()
            flash(f'Error validasi: {str(ve)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error impor: {str(e)}', 'danger')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    return render_template('admin/bahan/upload.html')

# --- CRUD ALAT ---
@app.route('/admin/alat')
@app.route('/admin/alat/<lab>')
@login_required
def alat_list(lab=None):
    valid_labs = ['Fisika', 'Kimia', 'Biologi']
    if lab and lab in valid_labs:
        alat = Alat.query.filter_by(nama_lab=lab).all()
    else:
        lab = "Semua"
        alat = Alat.query.all()
    return render_template('admin/alat/list.html', alat=alat, lab=lab)

@app.route('/admin/alat/create/<lab>', methods=['GET', 'POST'])
@login_required
def alat_create(lab):
    if request.method == 'POST':
        kode = request.form['kode']
        existing_alat = Alat.query.filter_by(kode=kode).first()
        if existing_alat:
            flash(f'Kode "{kode}" sudah digunakan.', 'danger')
            return render_template('admin/alat/create_alat.html', title=f"Tambah Alat ({lab})", lab=lab, satuan_alat=SATUAN_ALAT)
        try:
            satuan = request.form['satuan']
            if satuan == 'custom':
                satuan_manual = request.form.get('satuan_manual', '').strip()
                if not satuan_manual:
                    flash('Satuan manual tidak boleh kosong!', 'danger')
                    return render_template('admin/alat/create_alat.html', title=f"Tambah Alat ({lab})", lab=lab, satuan_alat=SATUAN_ALAT)
                satuan = satuan_manual
            a = Alat(
                kode=kode,
                nama_alat=request.form['nama_alat'],
                satuan=satuan,
                kuantitas=int(request.form['kuantitas']),
                tgl_masuk=datetime.strptime(request.form['tgl_masuk'], '%Y-%m-%d').date(),
                status=request.form.get('status', 'baik'),
                catatan=request.form.get('catatan', ''),
                nama_lab=lab
            )
            db.session.add(a)
            db.session.commit()
            flash(f'Alat {lab} berhasil ditambahkan!', 'success')
            return redirect(url_for('alat_list', lab=lab))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    return render_template('admin/alat/create_alat.html', title=f"Tambah Alat ({lab})", lab=lab, satuan_alat=SATUAN_ALAT)

@app.route('/admin/alat/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def alat_edit(id):
    a = Alat.query.get_or_404(id)
    lab = a.nama_lab
    if request.method == 'POST':
        try:
            a.kode = request.form['kode']
            a.nama_alat = request.form['nama_alat']
            a.satuan = request.form['satuan']
            if a.satuan == 'custom':
                satuan_manual = request.form.get('satuan_manual', '').strip()
                if not satuan_manual:
                    flash('Satuan manual tidak boleh kosong!', 'danger')
                    return render_template('admin/alat/edit_alat.html', title="Edit Alat", alat=a, satuan_alat=SATUAN_ALAT)
                a.satuan = satuan_manual
            a.tgl_masuk = datetime.strptime(request.form['tgl_masuk'], '%Y-%m-%d').date()
            a.catatan = request.form.get('catatan', '')

            status_action = request.form.get('status_action')
            jumlah_ubah = request.form.get('jumlah_ubah')
            if status_action and jumlah_ubah:
                jumlah_ubah = int(jumlah_ubah)
                if jumlah_ubah > a.kuantitas:
                    flash(f'Jumlah tidak boleh melebihi total kuantitas ({a.kuantitas})!', 'danger')
                    return render_template('admin/alat/edit_alat.html', title="Edit Alat", alat=a, satuan_alat=SATUAN_ALAT)
                if status_action == 'rusak':
                    if jumlah_ubah > (a.kuantitas - a.rusak):
                        flash(f'Hanya {a.kuantitas - a.rusak} alat yang dalam kondisi baik untuk dirusakkan!', 'danger')
                        return render_template('admin/alat/edit_alat.html', title="Edit Alat", alat=a, satuan_alat=SATUAN_ALAT)
                    a.rusak += jumlah_ubah
                    acara = BeritaAcara(
                        tanggal=datetime.now().date(),
                        jenis='alat',
                        item_id=a.id,
                        nama_item=a.nama_alat,
                        alasan='Rusak',
                        keterangan=f'{jumlah_ubah} unit alat {a.nama_alat} (Kode: {a.kode}) telah rusak.',
                        nama_petugas=current_user.id
                    )
                    db.session.add(acara)
                elif status_action == 'baik':
                    if jumlah_ubah > a.rusak:
                        flash(f'Hanya {a.rusak} alat yang rusak untuk diperbaiki!', 'danger')
                        return render_template('admin/alat/edit_alat.html', title="Edit Alat", alat=a, satuan_alat=SATUAN_ALAT)
                    a.rusak -= jumlah_ubah

            db.session.commit()
            flash('Alat berhasil diperbarui!', 'success')
            return redirect(url_for('alat_list', lab=lab))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    return render_template('admin/alat/edit_alat.html', title="Edit Alat", alat=a, satuan_alat=SATUAN_ALAT)

@app.route('/admin/alat/delete/<int:id>', methods=['POST'])
@login_required
def alat_delete(id):
    a = Alat.query.get_or_404(id)
    lab = a.nama_lab
    db.session.delete(a)
    db.session.commit()
    flash('Alat berhasil dihapus!', 'success')
    return redirect(url_for('alat_list', lab=lab))


# app.py

@app.route('/admin/alat/upload', methods=['GET', 'POST'])
@login_required
def alat_upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.xlsx'):
            flash('File Excel (.xlsx) diperlukan.', 'danger')
            return redirect(request.url)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        try:
            df = pd.read_excel(filepath)

            # ✅ Validasi kolom wajib
            required_columns = ['kode', 'nama_alat', 'satuan', 'kuantitas', 'tgl_masuk']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                flash(f'File tidak memiliki kolom wajib: {", ".join(missing_columns)}', 'danger')
                raise ValueError("Kolom wajib tidak lengkap")

            for _, row in df.iterrows():
                # ✅ Validasi dan ambil data
                kode = str(row['kode']).strip()
                nama_alat = str(row['nama_alat']).strip()
                satuan = str(row['satuan']).strip() if 'satuan' in row and pd.notna(row['satuan']) and str(row['satuan']).strip() != '' else 'item'
                kuantitas = int(row['kuantitas'])
                tgl_masuk = pd.to_datetime(row['tgl_masuk']).date()
                status = str(row['status']).strip() if 'status' in row else 'baik'
                catatan = str(row['catatan']).strip() if 'catatan' in row else ''
                nama_lab = str(row['nama_lab']).strip() if 'nama_lab' in row else 'Fisika'

                # ✅ Validasi data dasar
                if not kode or not nama_alat:
                    flash(f'Baris {_+1}: Kode dan Nama Alat wajib diisi.', 'danger')
                    continue
                if kuantitas <= 0:
                    flash(f'Baris {_+1}: Kuantitas harus lebih dari 0.', 'danger')
                    continue

                # ✅ Buat objek Alat
                a = Alat(
                    kode=kode,
                    nama_alat=nama_alat,
                    satuan=satuan,
                    kuantitas=kuantitas,
                    tgl_masuk=tgl_masuk,
                    status=status,
                    catatan=catatan,
                    nama_lab=nama_lab,
                    total_digunakan=0,
                    sedang_dipakai=0,
                    rusak=0
                )
                db.session.add(a)
            db.session.commit()
            flash('Data alat berhasil diimpor!', 'success')
            delete_file_after_delay(filepath, delay=5.0)
            return redirect(url_for('alat_list'))
        except ValueError as ve:
            db.session.rollback()
            flash(f'Error validasi: {str(ve)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error impor: {str(e)}', 'danger')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    return render_template('admin/alat/upload.html')

# --- CRUD KEJADIAN ---
@app.route('/admin/kejadian')
@app.route('/admin/kejadian/<lab>')
@login_required
def kejadian_list(lab=None):
    """
    Menampilkan daftar kejadian.
    Jika <lab> adalah 'Fisika', 'Kimia', atau 'Biologi', filter berdasarkan lab.
    Jika <lab> tidak diberikan atau tidak valid, tampilkan semua kejadian.
    """
    valid_labs = ['Fisika', 'Kimia', 'Biologi']
    
    if lab and lab in valid_labs:
        # Filter kejadian berdasarkan nama_lab
        kejadian = Kejadian.query.filter_by(nama_lab=lab).all()
    else:
        # Jika lab tidak valid atau tidak diberikan, tampilkan semua
        lab = "Semua" 
        kejadian = Kejadian.query.all()
        
    # Render template dengan data kejadian dan info lab
    return render_template('admin/kejadian/list.html', kejadian=kejadian, lab=lab)


# app.py

# app.py

@app.route('/admin/kejadian/create', methods=['GET', 'POST'])
@app.route('/admin/kejadian/create/<lab>', methods=['GET', 'POST'])
@login_required
def kejadian_create(lab=None):
    """
    Menangani pembuatan kejadian baru.
    """
    valid_labs = ['Fisika', 'Kimia', 'Biologi']
    
    # Tentukan lab awal berdasarkan URL atau default
    if request.method == 'POST':
        # Saat POST, lab diambil dari hidden field di form untuk konsistensi
        # Meskipun lab sebenarnya sudah ditentukan dari URL, ini memastikan tidak ada manipulasi
        # Dan menyederhanakan logika dropdown alat.
        selected_lab = request.form.get('nama_lab', 'Fisika')
        if selected_lab not in valid_labs:
             selected_lab = 'Fisika' # Fallback jika hidden field diubah
    else:
        # Saat GET, gunakan lab dari URL
        if lab and lab in valid_labs:
            selected_lab = lab
        else:
            # Jika lab tidak valid atau tidak diberikan, redirect ke lab default
            # atau Anda bisa menampilkan pilihan lab. Di sini kita pilih Fisika.
            return redirect(url_for('kejadian_create', lab='Fisika'))
            
    # Ambil daftar alat untuk lab yang dipilih
    alat_list = Alat.query.filter_by(nama_lab=selected_lab).all()
    
    # === Ambil daftar guru dan kelas untuk dropdown ===
    guru_list = Guru.query.all()
    kelas_list = Kelas.query.all()
    
    # === Definisikan daftar sesi (times) untuk dropdown ===
    times = [
        '07:10 - 07:50', '07:50 - 08:30', '08:30 - 09:10', '09:10 - 09:50',
        '10:10 - 10:50', '10:50 - 11:30', '11:30 - 12:10', '12:50 - 13:30',
        '13:30 - 14:10', '14:10 - 14:50', '14:50 - 15:30'
    ]

    if request.method == 'POST':
        try:
            # --- Validasi dan Pengambilan Data dari Form ---
            tanggal_kejadian_str = request.form['tanggal_kejadian']
            nama_guru = request.form['nama_guru'].strip()
            kelas = request.form['kelas'].strip()
            sesi = request.form['sesi'].strip()
            alat_id_str = request.form['alat_id']
            kuantitas_rusak_str = request.form['kuantitas_rusak']
            deskripsi = request.form.get('deskripsi', '').strip()
            status = request.form.get('status', 'belum ditangani')

            # --- Validasi Data Dasar ---
            if not all([tanggal_kejadian_str, nama_guru, kelas, sesi, alat_id_str, kuantitas_rusak_str]):
                flash('Harap isi semua kolom yang wajib (*).', 'danger')
                raise ValueError("Data tidak lengkap")

            tanggal_kejadian = datetime.strptime(tanggal_kejadian_str, '%Y-%m-%d').date()
            alat_id = int(alat_id_str)
            kuantitas_rusak = int(kuantitas_rusak_str)

            if kuantitas_rusak <= 0:
                 flash('Jumlah alat rusak harus lebih dari 0.', 'danger')
                 raise ValueError("Jumlah rusak tidak valid")

            # --- Buat Objek Kejadian ---
            k = Kejadian(
                tanggal_kejadian=tanggal_kejadian,
                nama_guru=nama_guru,
                kelas=kelas,
                sesi=sesi,
                alat_id=alat_id,
                kuantitas_rusak=kuantitas_rusak,
                deskripsi=deskripsi,
                status=status,
                nama_lab=selected_lab # Diambil dari URL/form awal
            )
            db.session.add(k)
            db.session.flush() # Dapatkan ID kejadian untuk keperluan log (opsional)

            # === Sinkronisasi dengan Berita Acara ===
            # Buat keterangan unik berdasarkan detail kejadian untuk pencocokan
            alat_obj = Alat.query.get(alat_id)
            nama_alat_str = alat_obj.nama_alat if alat_obj else "Tidak Diketahui"
            kode_alat_str = alat_obj.kode if alat_obj else "N/A"
            
            # Keterangan unik untuk mencegah duplikasi Berita Acara untuk kejadian yang sama
            keterangan_unik = f"Dari kejadian ID {k.id}: {kuantitas_rusak} unit alat {nama_alat_str} (Kode: {kode_alat_str}) rusak. {deskripsi}"

            # Cek apakah sudah ada Berita Acara untuk alat ini dengan keterangan unik ini
            existing_acara = BeritaAcara.query.filter_by(
                jenis='alat',
                item_id=alat_id,
                alasan='Rusak',
                keterangan=keterangan_unik
            ).first()

            if not existing_acara:
                # Jika belum ada, buat baru
                acara = BeritaAcara(
                    tanggal=tanggal_kejadian,
                    jenis='alat',
                    item_id=alat_id,
                    nama_item=nama_alat_str,
                    alasan='Rusak',
                    keterangan=keterangan_unik,
                    nama_petugas=getattr(current_user, 'id', 'System') # Ganti dengan nama user jika ada
                )
                db.session.add(acara)
            
            # Update status alat menjadi 'rusak' jika belum
            # (Catatan: Logika ini bisa disesuaikan. Misalnya, hanya alat yang benar-benar rusak saat ini)
            # Untuk saat ini, kita asumsikan kejadian membuat alat rusak.
            if alat_obj and alat_obj.status != 'rusak':
                 alat_obj.status = 'rusak'

            db.session.commit()
            flash(f'Kejadian di Lab {selected_lab} berhasil ditambahkan!', 'success')
            return redirect(url_for('kejadian_list', lab=selected_lab))
        except ValueError as ve:
            db.session.rollback()
            flash(f'Input tidak valid: {str(ve)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saat menyimpan kejadian: {str(e)}', 'danger')
            # Opsional: Log error untuk debugging
            # app.logger.error(f"Error di kejadian_create: {str(e)}")
            
    # GET request atau jika ada error validasi
    # Kirim semua data yang diperlukan ke template
    return render_template(
        'admin/kejadian/create_kejadian.html', # ✅ Template khusus create
        title=f"Tambah Kejadian ({selected_lab})", 
        alat_list=alat_list, 
        lab=selected_lab,
        guru_list=guru_list, # ✅ Kirim daftar guru
        kelas_list=kelas_list, # ✅ Kirim daftar kelas
        times=times # ✅ Kirim daftar sesi
    )


@app.route('/admin/kejadian/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def kejadian_edit(id):
    """
    Menangani pengeditan kejadian.
    """
    k = Kejadian.query.get_or_404(id)
    # Ambil daftar alat untuk lab kejadian asli (tidak berubah)
    alat_list = Alat.query.filter_by(nama_lab=k.nama_lab).all()
    
    if request.method == 'POST':
        try:
            # Simpan nilai lama untuk perbandingan
            old_kuantitas_rusak = k.kuantitas_rusak
            old_status = k.status
            old_deskripsi = k.deskripsi
            
            # Update data kejadian
            k.tanggal_kejadian = datetime.strptime(request.form['tanggal_kejadian'], '%Y-%m-%d').date()
            k.nama_guru = request.form['nama_guru'].strip()
            k.kelas = request.form['kelas'].strip()
            k.sesi = request.form['sesi'].strip()
            k.alat_id = int(request.form['alat_id'])
            k.kuantitas_rusak = int(request.form['kuantitas_rusak'])
            k.deskripsi = request.form.get('deskripsi', '').strip()
            k.status = request.form.get('status', 'belum ditangani')
            
            # === Sinkronisasi dengan Berita Acara ===
            alat_obj = Alat.query.get(k.alat_id)
            nama_alat_str = alat_obj.nama_alat if alat_obj else "Tidak Diketahui"
            kode_alat_str = alat_obj.kode if alat_obj else "N/A"
            
            if k.kuantitas_rusak > old_kuantitas_rusak:
                # Jika jumlah rusak bertambah, buat Berita Acara tambahan
                delta_rusak = k.kuantitas_rusak - old_kuantitas_rusak
                keterangan_tambahan = f"Tambahan {delta_rusak} unit alat {nama_alat_str} (Kode: {kode_alat_str}) rusak dari kejadian ID {k.id}. {k.deskripsi}"
                
                acara_tambahan = BeritaAcara(
                    tanggal=k.tanggal_kejadian,
                    jenis='alat',
                    item_id=k.alat_id,
                    nama_item=nama_alat_str,
                    alasan='Rusak',
                    keterangan=keterangan_tambahan,
                    nama_petugas=getattr(current_user, 'id', 'System')
                )
                db.session.add(acara_tambahan)
            
            # Update status alat jika diperlukan
            if alat_obj:
                # Misalnya, jika status kejadian diubah menjadi 'sudah diperbaiki',
                # kita bisa memperbarui status alat atau berita acara.
                # Untuk saat ini, kita hanya update status alat jika kejadian 'rusak'.
                if k.status == 'sudah diperbaiki':
                     # Contoh: Update Berita Acara jika status kejadian 'sudah diperbaiki'
                     # Cari Berita Acara berdasarkan ID alat dan tanggal/status awal
                     # Ini adalah contoh logika, sesuaikan dengan kebutuhan spesifik Anda
                     # Misalnya, cari berdasarkan keterangan unik dari saat create
                     keterangan_awal = f"Dari kejadian ID {k.id}: {old_kuantitas_rusak} unit alat {nama_alat_str} (Kode: {kode_alat_str}) rusak. {old_deskripsi}"
                     acara = BeritaAcara.query.filter_by(
                         jenis='alat',
                         item_id=k.alat_id,
                         alasan='Rusak',
                         keterangan=keterangan_awal
                     ).first()
                     if acara:
                         acara.status_follow_up = 'Sudah Ditangani' # Sesuaikan field jika berbeda
                         # Anda bisa update kuantitas_tindakan, tanggal_tindakan, dll jika ada
                elif alat_obj.status != 'rusak':
                    # Jika alat belum rusak dan kejadian tetap 'belum ditangani' atau 'rusak', ubah statusnya
                    alat_obj.status = 'rusak'

            db.session.commit()
            flash('Kejadian berhasil diperbarui!', 'success')
            return redirect(url_for('kejadian_list', lab=k.nama_lab))
        except ValueError as ve:
            db.session.rollback()
            flash(f'Input tidak valid: {str(ve)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saat memperbarui kejadian: {str(e)}', 'danger')
            
    # GET request
    return render_template(
        'admin/kejadian/edit_kejadian.html', # ✅ Template khusus edit
        title="Edit Kejadian", 
        kejadian=k, 
        alat_list=alat_list
    )


@app.route('/admin/kejadian/delete/<int:id>', methods=['POST'])
@login_required
def kejadian_delete(id):
    """
    Menghapus sebuah kejadian.
    """
    k = Kejadian.query.get_or_404(id)
    lab = k.nama_lab
    try:
        db.session.delete(k)
        db.session.commit()
        flash('Kejadian berhasil dihapus!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saat menghapus kejadian: {str(e)}', 'danger')
    return redirect(url_for('kejadian_list', lab=lab))

# --- AKHIR CRUD KEJADIAN ---


# app.py

@app.route('/admin/kejadian/upload', methods=['GET', 'POST'])
@login_required
def kejadian_upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.xlsx'):
            flash('File Excel (.xlsx) diperlukan.', 'danger')
            return redirect(request.url)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        try:
            df = pd.read_excel(filepath)

            # ✅ Validasi kolom wajib
            required_columns = ['tanggal_kejadian', 'nama_guru', 'kelas', 'sesi', 'alat_id', 'kuantitas_rusak', 'nama_lab']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                flash(f'File tidak memiliki kolom wajib: {", ".join(missing_columns)}', 'danger')
                raise ValueError("Kolom wajib tidak lengkap")

            for _, row in df.iterrows():
                # ✅ Validasi dan ambil data
                tanggal_kejadian = pd.to_datetime(row['tanggal_kejadian']).date()
                nama_guru = str(row['nama_guru']).strip()
                kelas = str(row['kelas']).strip()
                sesi = str(row['sesi']).strip()
                
                # ✅ Cari alat berdasarkan kode (bukan ID)
                kode_alat = str(row['alat_id']).strip()
                alat = Alat.query.filter_by(kode=kode_alat).first()
                if not alat:
                    flash(f'Baris {_+1}: Kode Alat "{kode_alat}" tidak ditemukan.', 'danger')
                    continue
                alat_id = alat.id  # ✅ Gunakan ID database
                
                kuantitas_rusak = int(row['kuantitas_rusak'])
                deskripsi = str(row['deskripsi']).strip() if 'deskripsi' in row else ''
                status = str(row['status']).strip() if 'status' in row else 'belum ditangani'
                nama_lab = str(row['nama_lab']).strip() if 'nama_lab' in row else 'Fisika'

                # ✅ Validasi data dasar
                if not nama_guru or not kelas or not sesi:
                    flash(f'Baris {_+1}: Nama Guru, Kelas, dan Sesi wajib diisi.', 'danger')
                    continue
                if kuantitas_rusak <= 0:
                    flash(f'Baris {_+1}: Kuantitas Rusak harus lebih dari 0.', 'danger')
                    continue
                if nama_lab not in ['Fisika', 'Kimia', 'Biologi']:
                    flash(f'Baris {_+1}: Nama Lab harus "Fisika", "Kimia", atau "Biologi".', 'danger')
                    continue

                # ✅ Buat objek Kejadian
                k = Kejadian(
                    tanggal_kejadian=tanggal_kejadian,
                    nama_guru=nama_guru,
                    kelas=kelas,
                    sesi=sesi,
                    alat_id=alat_id,  # ✅ Gunakan ID database
                    kuantitas_rusak=kuantitas_rusak,
                    deskripsi=deskripsi,
                    status=status,
                    nama_lab=nama_lab
                )
                db.session.add(k)

                # ✅ Sinkronisasi: Update status alat menjadi 'rusak'
                if alat and alat.status != 'rusak':
                    alat.status = 'rusak'
                    alat.rusak += kuantitas_rusak  # Tambah ke kolom rusak

            db.session.commit()
            flash('Data kejadian berhasil diimpor!', 'success')
            delete_file_after_delay(filepath, delay=5.0)
            return redirect(url_for('kejadian_list'))
        except ValueError as ve:
            db.session.rollback()
            flash(f'Error validasi: {str(ve)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error impor: {str(e)}', 'danger')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    return render_template('admin/kejadian/upload.html')


# --- BOOKING & CANCEL ---
@app.route('/booking', methods=['GET', 'POST'])
@login_required
def booking_form():
    guru_list = Guru.query.all()
    kelas_list = Kelas.query.all()
    day = request.args.get('day')
    date_str = request.args.get('date')
    time_slot = request.args.get('time')
    lab = request.args.get('lab', 'Fisika')
    times = [
        '07:10 - 07:50', '07:50 - 08:30', '08:30 - 09:10', '09:10 - 09:50',
        '10:10 - 10:50', '10:50 - 11:30', '11:30 - 12:10', '12:50 - 13:30',
        '13:30 - 14:10', '14:10 - 14:50', '14:50 - 15:30'
    ]
    semua_alat = Alat.query.all()
    semua_bahan = Bahan.query.all()

    if request.method == 'POST':
        try:
            try:
                tanggal = datetime.strptime(f"{date_str} 2025", "%d %b %Y").date()
            except ValueError:
                tanggal = datetime.strptime(f"{date_str} 2026", "%d %b %Y").date()

            nama_guru = request.form['nama_guru']
            kelas = request.form['kelas']
            judul_praktikum = request.form['judul_praktikum']
            jumlah_kelompok = int(request.form['jumlah_kelompok'])
            sesi_pilihan = request.form.getlist('sesi_pilihan')

            if not sesi_pilihan:
                flash('Harap pilih minimal 1 sesi!', 'danger')
                return render_template('booking_form.html',
                    day=day, date=date_str, time_slot=time_slot, lab=lab,
                    times=times, semua_alat=semua_alat, semua_bahan=semua_bahan,
                    guru_list=guru_list, kelas_list=kelas_list)

            alat_ids = request.form.getlist('alat_id')
            bahan_ids = request.form.getlist('bahan_id')

            if not alat_ids and not bahan_ids:
                flash('Harap pilih minimal 1 alat atau bahan!', 'danger')
                return render_template('booking_form.html',
                    day=day, date=date_str, time_slot=time_slot, lab=lab,
                    times=times, semua_alat=semua_alat, semua_bahan=semua_bahan,
                    guru_list=guru_list, kelas_list=kelas_list)

            for sesi in sesi_pilihan:
                existing = JadwalPenggunaan.query.filter_by(
                    tanggal=tanggal,
                    nama_lab=lab,
                    sesi=sesi,
                    nama_guru=nama_guru
                ).first()
                if existing:
                    flash(f'Maaf, Anda sudah memesan sesi {sesi} pada hari ini.', 'warning')
                    return render_template('booking_form.html',
                        day=day, date=date_str, time_slot=time_slot, lab=lab,
                        times=times, semua_alat=semua_alat, semua_bahan=semua_bahan,
                        guru_list=guru_list, kelas_list=kelas_list)

            validation_errors = []
            for alat_id in alat_ids:
                kuantitas = int(request.form.get(f'kuantitas_alat_{alat_id}', 1))
                alat = Alat.query.get(alat_id)
                if not alat or alat.tersedia_baik < kuantitas:
                    validation_errors.append(f'Stok alat {alat.nama_alat if alat else "Tidak dikenal"} tidak cukup!')
            for bahan_id in bahan_ids:
                kuantitas = float(request.form.get(f'kuantitas_bahan_{bahan_id}', 0.1))
                bahan = Bahan.query.get(bahan_id)
                if not bahan or bahan.sisa_tersedia < kuantitas:
                    validation_errors.append(f'Stok bahan {bahan.nama_bahan if bahan else "Tidak dikenal"} tidak cukup!')

            if validation_errors:
                for err in validation_errors:
                    flash(err, 'danger')
                return render_template('booking_form.html',
                    day=day, date=date_str, time_slot=time_slot, lab=lab,
                    times=times, semua_alat=semua_alat, semua_bahan=semua_bahan,
                    guru_list=guru_list, kelas_list=kelas_list)

            for sesi in sesi_pilihan:
                jadwal = JadwalPenggunaan(
                    tanggal=tanggal,
                    nama_guru=nama_guru,
                    sesi=sesi,
                    kelas=kelas,
                    judul_praktikum=judul_praktikum,
                    jumlah_kelompok=jumlah_kelompok,
                    nama_lab=lab
                )
                db.session.add(jadwal)
                db.session.flush()

                for alat_id in alat_ids:
                    kuantitas = int(request.form.get(f'kuantitas_alat_{alat_id}', 1))
                    alat = Alat.query.get(alat_id)
                    if alat:
                        alat.sedang_dipakai += kuantitas
                        alat.total_digunakan += kuantitas
                        jadwal_alat = JadwalAlat(
                            jadwal_id=jadwal.id,
                            alat_id=alat_id,
                            kuantitas_digunakan=kuantitas
                        )
                        db.session.add(jadwal_alat)

                for bahan_id in bahan_ids:
                    kuantitas = float(request.form.get(f'kuantitas_bahan_{bahan_id}', 0.1))
                    bahan = Bahan.query.get(bahan_id)
                    if bahan:
                        bahan.total_digunakan += kuantitas
                        jadwal_bahan = JadwalBahan(
                            jadwal_id=jadwal.id,
                            bahan_id=bahan_id,
                            kuantitas_digunakan=kuantitas
                        )
                        db.session.add(jadwal_bahan)

            db.session.commit()
            flash(f'✅ Jadwal berhasil dipesan untuk {len(sesi_pilihan)} sesi!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ Terjadi kesalahan: {str(e)}', 'danger')
            return render_template('booking_form.html',
                day=day, date=date_str, time_slot=time_slot, lab=lab,
                times=times, semua_alat=semua_alat, semua_bahan=semua_bahan,
                guru_list=guru_list, kelas_list=kelas_list)

    return render_template('booking_form.html',
        day=day,
        date=date_str,
        time_slot=time_slot,
        lab=lab,
        times=times,
        semua_alat=semua_alat,
        semua_bahan=semua_bahan,
        guru_list=guru_list,
        kelas_list=kelas_list)

@app.route('/cancel/<int:id>', methods=['POST'])
@login_required
def cancel_booking(id):
    jadwal = JadwalPenggunaan.query.get_or_404(id)
    restore_stock(jadwal)
    db.session.delete(jadwal)
    db.session.commit()
    flash('Jadwal berhasil dibatalkan!', 'success')
    return redirect(url_for('dashboard'))

# --- REQUEST LAB ---
@app.route('/requests')
@login_required
def lab_requests():
    jadwals = JadwalPenggunaan.query.order_by(JadwalPenggunaan.tanggal.desc()).all()
    now = datetime.now()
    for j in jadwals:
        sesi_end = parse_sesi_end(j.sesi)
        auto_complete_time = datetime.combine(j.tanggal, sesi_end) + timedelta(minutes=5)
        if j.status_request == 'menunggu' and now >= auto_complete_time:
            j.status_request = 'selesai'
        sesi_start = parse_sesi_start(j.sesi)
        cancel_deadline = datetime.combine(j.tanggal, sesi_start) + timedelta(hours=2)
        j.can_cancel = (j.tanggal == now.date()) and (now <= cancel_deadline) and (j.status_request == 'menunggu')
    db.session.commit()
    return render_template('lab_requests/list.html', jadwals=jadwals)

@app.route('/requests/update/<int:id>', methods=['POST'])
@login_required
def update_request_status(id):
    jadwal = JadwalPenggunaan.query.get_or_404(id)
    new_status = request.form.get('status_request')
    if new_status in ['menunggu', 'tidak terlaksana']:
        if new_status == 'tidak terlaksana':
            restore_stock(jadwal)
        jadwal.status_request = new_status
        db.session.commit()
        flash('Status request diperbarui!', 'success')
    return redirect(url_for('lab_requests'))

@app.route('/requests/cancel/<int:id>', methods=['POST'])
@login_required
def cancel_request(id):
    jadwal = JadwalPenggunaan.query.get_or_404(id)
    if jadwal.status_request == 'menunggu':
        restore_stock(jadwal)
        jadwal.status_request = 'dibatalkan'
        db.session.commit()
        flash('Request berhasil dibatalkan!', 'info')
    return redirect(url_for('lab_requests'))

# --- BERITA ACARA ---
@app.route('/berita-acara')
@login_required
def berita_acara_list():
    acara = BeritaAcara.query.order_by(BeritaAcara.tanggal.desc()).all()
    return render_template('berita_acara/list.html', acara=acara)

@app.route('/berita-acara/create', methods=['GET', 'POST'])
@login_required
def berita_acara_create():
    if request.method == 'POST':
        try:
            jenis = request.form['jenis']
            item_id = int(request.form['item_id'])
            alasan = request.form['alasan']
            keterangan = request.form.get('keterangan', '')
            nama_petugas = request.form['nama_petugas']
            if jenis == 'bahan':
                item = Bahan.query.get_or_404(item_id)
                nama_item = item.nama_bahan
                item.status_expired = 'expired'
            else:
                item = Alat.query.get_or_404(item_id)
                nama_item = item.nama_alat
                item.status = 'rusak'
            acara = BeritaAcara(
                tanggal=datetime.now().date(),
                jenis=jenis,
                item_id=item_id,
                nama_item=nama_item,
                alasan=alasan,
                keterangan=keterangan,
                nama_petugas=nama_petugas
            )
            db.session.add(acara)
            db.session.commit()
            flash('Berita acara berhasil disimpan!', 'success')
            return redirect(url_for('berita_acara_list'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    bahan_expired = Bahan.query.filter_by(status_expired='belum expired').all()
    alat_rusak = Alat.query.filter_by(status='baik').all()
    return render_template('berita_acara/form.html', bahan_expired=bahan_expired, alat_rusak=alat_rusak)


@app.route('/berita-acara/upload', methods=['GET', 'POST'])
@login_required
def berita_acara_upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.xlsx'):
            flash('File Excel (.xlsx) diperlukan.', 'danger')
            return redirect(request.url)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        try:
            df = pd.read_excel(filepath)
            for _, row in df.iterrows():
                # ✅ Validasi dan ambil data
                tanggal = pd.to_datetime(row['tanggal']).date()
                jenis = str(row['jenis']).strip().lower()
                item_id = int(row['item_id'])
                nama_item = str(row['nama_item']).strip()
                alasan = str(row['alasan']).strip()
                keterangan = str(row['keterangan']).strip() if 'keterangan' in row else ''
                nama_petugas = str(row['nama_petugas']).strip()

                # ✅ Validasi data dasar
                if not nama_item or not alasan:
                    flash(f'Baris {_+1}: Nama Item dan Alasan wajib diisi.', 'danger')
                    continue
                if jenis not in ['bahan', 'alat']:
                    flash(f'Baris {_+1}: Jenis harus "bahan" atau "alat".', 'danger')
                    continue

                # ✅ Buat objek BeritaAcara
                acara = BeritaAcara(
                    tanggal=tanggal,
                    jenis=jenis,
                    item_id=item_id,
                    nama_item=nama_item,
                    alasan=alasan,
                    keterangan=keterangan,
                    nama_petugas=nama_petugas
                )
                db.session.add(acara)

                # ✅ Sinkronisasi: Update status item
                if jenis == 'bahan':
                    item = Bahan.query.get(item_id)
                    if item and item.status_expired != 'expired':
                        item.status_expired = 'expired'
                elif jenis == 'alat':
                    item = Alat.query.get(item_id)
                    if item and item.status != 'rusak':
                        item.status = 'rusak'
            db.session.commit()
            flash('Data berita acara berhasil diimpor!', 'success')
            delete_file_after_delay(filepath, delay=5.0)
            return redirect(url_for('berita_acara_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error impor: {str(e)}', 'danger')
            if os.path.exists(filepath):
                os.remove(filepath)
    return render_template('berita_acara/upload.html')



@app.route('/berita-acara/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def berita_acara_edit(id):
    acara = BeritaAcara.query.get_or_404(id)
    if request.method == 'POST':
        try:
            acara.status_follow_up = request.form['status_follow_up']
            acara.kuantitas_tindakan = int(request.form['kuantitas_tindakan'])
            tgl_tindakan_str = request.form.get('tanggal_tindakan')
            if tgl_tindakan_str:
                acara.tanggal_tindakan = datetime.strptime(tgl_tindakan_str, '%Y-%m-%d').date()
            else:
                acara.tanggal_tindakan = None
            acara.catatan_tindakan = request.form.get('catatan_tindakan', '')
            db.session.commit()
            flash('Berita acara berhasil diperbarui!', 'success')
            return redirect(url_for('berita_acara_list'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    return render_template('berita_acara/edit.html', acara=acara)

@app.route('/berita-acara/delete/<int:id>', methods=['POST'])
@login_required
def berita_acara_delete(id):
    acara = BeritaAcara.query.get_or_404(id)
    db.session.delete(acara)
    db.session.commit()
    flash('Berita acara berhasil dihapus!', 'success')
    return redirect(url_for('berita_acara_list'))

@app.route('/berita-acara/penghapusan/create', methods=['GET', 'POST'])
@login_required
def berita_acara_penghapusan_create():
    if request.method == 'POST':
        try:
            jenis = request.form['jenis']
            item_id = int(request.form['item_id'])
            alasan = request.form['alasan']
            keterangan = request.form.get('keterangan', '')
            nama_petugas = request.form['nama_petugas']
            if jenis == 'bahan':
                item = Bahan.query.get_or_404(item_id)
                nama_item = item.nama_bahan
                if item.status_expired != 'expired':
                    item.status_expired = 'expired'
            else:
                item = Alat.query.get_or_404(item_id)
                nama_item = item.nama_alat
                if item.status != 'rusak':
                    item.status = 'rusak'
            acara = BeritaAcara(
                tanggal=datetime.now().date(),
                jenis=jenis,
                item_id=item_id,
                nama_item=nama_item,
                alasan=alasan,
                keterangan=keterangan,
                nama_petugas=nama_petugas,
                status_follow_up='Belum Ditangani',
                kuantitas_tindakan=0,
                tanggal_tindakan=None,
                catatan_tindakan=''
            )
            db.session.add(acara)
            db.session.commit()
            flash('Berita acara penghapusan berhasil disimpan!', 'success')
            return redirect(url_for('berita_acara_list'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    bahan_list = Bahan.query.filter_by(status_expired='belum expired').all()
    alat_list = Alat.query.filter_by(status='baik').all()
    return render_template('berita_acara/penghapusan_form.html', bahan_list=bahan_list, alat_list=alat_list)

@app.route('/api/berita-acara/items/<jenis>')
@login_required
def api_berita_acara_items(jenis):
    if jenis == 'bahan':
        items = Bahan.query.filter(Bahan.status_expired != 'expired').all()
        data = [{'id': item.id, 'name': item.nama_bahan, 'kode': item.kode} for item in items]
    elif jenis == 'alat':
        items = Alat.query.filter(Alat.status != 'rusak').all()
        data = [{'id': item.id, 'name': item.nama_alat, 'kode': item.kode} for item in items]
    else:
        data = []
    return jsonify(data)

# --- JADWAL SELESAI ---

@app.route('/jadwal/selesai/<int:id>', methods=['POST'])
@login_required
def jadwal_selesai(id):
    jadwal = JadwalPenggunaan.query.get_or_404(id)
    laporan_penggunaan = request.form.get('laporan_penggunaan', '')
    laporan_kegiatan = request.form.get('laporan_kegiatan', '')
    alat_rusak_ids = request.form.getlist('alat_rusak')

    jadwal.laporan_penggunaan = laporan_penggunaan
    jadwal.laporan_kegiatan = laporan_kegiatan
    jadwal.status_eksperimen = 'selesai'

    for alat in jadwal.alat:
        jadwal_alat = JadwalAlat.query.filter_by(jadwal_id=jadwal.id, alat_id=alat.id).first()
        if not jadwal_alat:
            continue
        kuantitas = jadwal_alat.kuantitas_digunakan

        if str(alat.id) in alat_rusak_ids:
            # Alat rusak: pindahkan dari sedang_dipakai ke rusak
            alat.sedang_dipakai -= kuantitas
            alat.rusak += kuantitas
            alat.status = 'rusak'

            # ✅ Tambahkan: Buat Berita Acara otomatis saat alat rusak
            acara = BeritaAcara(
                tanggal=datetime.now().date(),
                jenis='alat',
                item_id=alat.id,
                nama_item=alat.nama_alat,
                alasan='Rusak',
                keterangan=f'{kuantitas} unit alat {alat.nama_alat} (Kode: {alat.kode}) rusak saat praktikum oleh {jadwal.nama_guru} di kelas {jadwal.kelas} sesi {jadwal.sesi}.',
                nama_petugas=current_user.id  # atau ganti dengan nama petugas yang valid
            )
            db.session.add(acara)
        else:
            # Alat baik: kembalikan ke tersedia (kurangi sedang_dipakai)
            alat.sedang_dipakai -= kuantitas

    db.session.commit()
    flash('Eksperimen ditandai selesai!', 'success')
    return redirect(url_for('dashboard'))


# --- CRUD GURU & KELAS ---
@app.route('/admin/guru')
@login_required
def guru_list():
    guru = Guru.query.all()
    return render_template('admin/guru/list.html', guru=guru)
# app.py

@app.route('/admin/guru/create', methods=['GET', 'POST'])
@login_required
def guru_create():
    """
    Menambahkan guru baru.
    """
    if request.method == 'POST':
        try:
            # Ambil dan bersihkan input
            nama_guru = request.form['nama_guru'].strip()

            # Validasi: Cek apakah input kosong
            if not nama_guru:
                flash('Nama guru tidak boleh kosong.', 'danger')
                return render_template('admin/guru/form.html', title="Tambah Guru", guru=None)

            # Validasi: Cek apakah nama sudah ada
            existing = Guru.query.filter_by(nama_guru=nama_guru).first()
            if existing:
                flash(f'Guru "{nama_guru}" sudah ada.', 'danger')
                return render_template('admin/guru/form.html', title="Tambah Guru", guru=None)

            # Buat objek baru
            g = Guru(nama_guru=nama_guru)
            db.session.add(g)
            db.session.commit()
            
            flash(f'Guru "{nama_guru}" berhasil ditambahkan!', 'success')
            return redirect(url_for('guru_list'))
            
        except Exception as e:
            # Tangkap error lainnya
            db.session.rollback()
            flash(f'Terjadi kesalahan saat menambahkan guru: {str(e)}', 'danger')
            # Render ulang form dengan data yang sudah dimasukkan
            return render_template('admin/guru/form.html', title="Tambah Guru", guru=None)
            
    # GET request: Tampilkan form kosong
    return render_template('admin/guru/form.html', title="Tambah Guru", guru=None)



@app.route('/admin/guru/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def guru_edit(id):
    """
    Mengedit data guru.
    """
    # Ambil objek guru atau kembalikan 404 jika tidak ditemukan
    g = Guru.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Ambil dan bersihkan input
            nama_guru_baru = request.form['nama_guru'].strip()

            # Validasi: Cek apakah input kosong
            if not nama_guru_baru:
                flash('Nama guru tidak boleh kosong.', 'danger')
                return render_template('admin/guru/form.html', title="Edit Guru", guru=g)

            # Validasi: Cek apakah nama sudah ada (dan bukan milik diri sendiri)
            guru_sama = Guru.query.filter(Guru.id != id, Guru.nama_guru.ilike(nama_guru_baru)).first()
            if guru_sama:
                flash(f'Guru dengan nama "{nama_guru_baru}" sudah ada.', 'danger')
                return render_template('admin/guru/form.html', title="Edit Guru", guru=g)

            # Update data
            g.nama_guru = nama_guru_baru
            
            # Simpan ke database
            db.session.commit()
            
            flash(f'Guru "{nama_guru_baru}" berhasil diperbarui!', 'success')
            return redirect(url_for('guru_list'))
            
        except Exception as e:
            # Tangkap error lainnya
            db.session.rollback() # Batalkan perubahan jika terjadi error
            flash(f'Terjadi kesalahan saat memperbarui guru: {str(e)}', 'danger')
            # Render ulang form dengan data yang sudah dimasukkan
            return render_template('admin/guru/form.html', title="Edit Guru", guru=g)
    
    # GET request: Tampilkan form dengan data guru
    return render_template('admin/guru/form.html', title="Edit Guru", guru=g)

@app.route('/admin/guru/delete/<int:id>', methods=['POST'])
@login_required
def guru_delete(id):
    g = Guru.query.get_or_404(id)
    db.session.delete(g)
    db.session.commit()
    flash('Guru berhasil dihapus!', 'success')
    return redirect(url_for('guru_list'))

@app.route('/admin/kelas')
@login_required
def kelas_list():
    kelas = Kelas.query.all()
    return render_template('admin/kelas/list.html', kelas=kelas)

@app.route('/admin/kelas/create', methods=['GET', 'POST'])
@login_required
def kelas_create():
    if request.method == 'POST':
        nama_kelas = request.form['nama_kelas']
        existing = Kelas.query.filter_by(nama_kelas=nama_kelas).first()
        if existing:
            flash(f'Kelas "{nama_kelas}" sudah ada.', 'danger')
            return render_template('admin/kelas/form.html', title="Tambah Kelas", kelas=None)
        try:
            k = Kelas(nama_kelas=nama_kelas)
            db.session.add(k)
            db.session.commit()
            flash(f'Kelas "{nama_kelas}" berhasil ditambahkan!', 'success')
            return redirect(url_for('kelas_list'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    return render_template('admin/kelas/form.html', title="Tambah Kelas", kelas=None)

@app.route('/admin/kelas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def kelas_edit(id):
    k = Kelas.query.get_or_404(id)
    if request.method == 'POST':
        nama_kelas = request.form['nama_kelas']
        existing = Kelas.query.filter(Kelas.id != id, Kelas.nama_kelas == nama_kelas).first()
        if existing:
            flash(f'Kelas "{nama_kelas}" sudah ada.', 'danger')
            return render_template('admin/kelas/form.html', title="Edit Kelas", kelas=k)
        try:
            k.nama_kelas = nama_kelas
            db.session.commit()
            flash(f'Kelas "{nama_kelas}" berhasil diperbarui!', 'success')
            return redirect(url_for('kelas_list'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    return render_template('admin/kelas/form.html', title="Edit Kelas", kelas=k)

@app.route('/admin/kelas/delete/<int:id>', methods=['POST'])
@login_required
def kelas_delete(id):
    k = Kelas.query.get_or_404(id)
    db.session.delete(k)
    db.session.commit()
    flash('Kelas berhasil dihapus!', 'success')
    return redirect(url_for('kelas_list'))

# --- DOWNLOAD & UPLOAD EXCEL ---
@app.route('/download/excel/<table_name>')
@login_required
def download_excel(table_name):
    if table_name not in ['bahan', 'alat', 'kejadian']:
        flash('Tabel tidak dikenali.', 'danger')
        return redirect(url_for('admin_index'))
    if table_name == 'bahan':
        data = Bahan.query.all()
        columns = ['kode', 'nama_bahan', 'kuantitas', 'tgl_masuk', 'tgl_expired', 'status_expired', 'catatan', 'nama_lab']
    elif table_name == 'alat':
        data = Alat.query.all()
        columns = ['kode', 'nama_alat', 'kuantitas', 'tgl_masuk', 'status', 'catatan', 'nama_lab']
    else:
        data = Kejadian.query.all()
        columns = ['tanggal_kejadian', 'nama_guru', 'kelas', 'sesi', 'alat_id', 'kuantitas_rusak', 'deskripsi', 'status', 'nama_lab']
    rows = [{col: getattr(item, col, '') for col in columns} for item in data]
    df = pd.DataFrame(rows, columns=columns)
    filename = f"{table_name}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    df.to_excel(filepath, index=False)
    delete_file_after_delay(filepath, delay=5)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/download/all/excel')
@login_required
def download_all_excel():
    bahan_df = pd.DataFrame([{col: getattr(b, col, '') for col in ['kode', 'nama_bahan', 'kuantitas', 'tgl_masuk', 'tgl_expired', 'status_expired', 'catatan', 'nama_lab']} for b in Bahan.query.all()])
    alat_df = pd.DataFrame([{col: getattr(a, col, '') for col in ['kode', 'nama_alat', 'kuantitas', 'tgl_masuk', 'status', 'catatan', 'nama_lab']} for a in Alat.query.all()])
    kejadian_df = pd.DataFrame([{col: getattr(k, col, '') for col in ['tanggal_kejadian', 'nama_guru', 'kelas', 'sesi', 'alat_id', 'kuantitas_rusak', 'deskripsi', 'status', 'nama_lab']} for k in Kejadian.query.all()])
    filename = f"all_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with pd.ExcelWriter(filepath) as writer:
        bahan_df.to_excel(writer, sheet_name='Bahan', index=False)
        alat_df.to_excel(writer, sheet_name='Alat', index=False)
        kejadian_df.to_excel(writer, sheet_name='Kejadian', index=False)
    delete_file_after_delay(filepath, delay=5)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/download/jadwal/<lab>')
@login_required
def download_jadwal_excel(lab):
    if lab not in ['Fisika', 'Kimia', 'Biologi', 'Semua']:
        flash('Lab tidak dikenali.', 'danger')
        return redirect(url_for('dashboard'))
    if lab == 'Semua':
        jadwals = JadwalPenggunaan.query.all()
    else:
        jadwals = JadwalPenggunaan.query.filter_by(nama_lab=lab).all()
    rows = [{'tanggal': j.tanggal, 'nama_guru': j.nama_guru, 'sesi': j.sesi, 'kelas': j.kelas, 'judul_praktikum': j.judul_praktikum, 'jumlah_kelompok': j.jumlah_kelompok, 'nama_lab': j.nama_lab} for j in jadwals]
    df = pd.DataFrame(rows)
    filename = f"jadwal_{lab}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    df.to_excel(filepath, index=False)
    delete_file_after_delay(filepath, delay=5)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/upload/all/excel', methods=['GET', 'POST'])
@login_required
def upload_all_excel():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.xlsx'):
            flash('File Excel (.xlsx) diperlukan.', 'danger')
            return redirect(request.url)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        try:
            xls = pd.ExcelFile(filepath)
            # === IMPOR BAHAN ===
            if 'Bahan' in xls.sheet_names:
                df_bahan = pd.read_excel(xls, 'Bahan')
                for _, row in df_bahan.iterrows():
                    kode = str(row['kode']).strip()
                    nama_bahan = str(row['nama_bahan']).strip()
                    satuan = str(row['satuan']).strip() if 'satuan' in row and pd.notna(row['satuan']) else 'pcs'
                    kuantitas = float(row['kuantitas'])
                    tgl_masuk = pd.to_datetime(row['tgl_masuk']).date()
                    tgl_expired = pd.to_datetime(row['tgl_expired']).date() if 'tgl_expired' in row and pd.notna(row['tgl_expired']) else None
                    status_expired = str(row['status_expired']).strip() if 'status_expired' in row else 'belum expired'
                    catatan = str(row['catatan']).strip() if 'catatan' in row else ''
                    nama_lab = str(row['nama_lab']).strip() if 'nama_lab' in row else 'Fisika'

                    if not kode or not nama_bahan:
                        flash(f'[Bahan] Baris {_+1}: Kode dan Nama Bahan wajib diisi.', 'danger')
                        continue
                    if kuantitas <= 0:
                        flash(f'[Bahan] Baris {_+1}: Kuantitas harus lebih dari 0.', 'danger')
                        continue

                    b = Bahan(
                        kode=kode,
                        nama_bahan=nama_bahan,
                        satuan=satuan,
                        kuantitas=kuantitas,
                        tgl_masuk=tgl_masuk,
                        tgl_expired=tgl_expired,
                        status_expired=status_expired,
                        catatan=catatan,
                        nama_lab=nama_lab,
                        total_digunakan=0.0
                    )
                    db.session.add(b)

            # === IMPOR ALAT ===
            if 'Alat' in xls.sheet_names:
                df_alat = pd.read_excel(xls, 'Alat')
                for _, row in df_alat.iterrows():
                    kode = str(row['kode']).strip()
                    nama_alat = str(row['nama_alat']).strip()
                    satuan = str(row['satuan']).strip() if 'satuan' in row and pd.notna(row['satuan']) and str(row['satuan']).strip() != '' else 'item'
                    kuantitas = int(row['kuantitas'])
                    tgl_masuk = pd.to_datetime(row['tgl_masuk']).date()
                    status = str(row['status']).strip() if 'status' in row else 'baik'
                    catatan = str(row['catatan']).strip() if 'catatan' in row else ''
                    nama_lab = str(row['nama_lab']).strip() if 'nama_lab' in row else 'Fisika'

                    if not kode or not nama_alat:
                        flash(f'[Alat] Baris {_+1}: Kode dan Nama Alat wajib diisi.', 'danger')
                        continue
                    if kuantitas <= 0:
                        flash(f'[Alat] Baris {_+1}: Kuantitas harus lebih dari 0.', 'danger')
                        continue

                    a = Alat(
                        kode=kode,
                        nama_alat=nama_alat,
                        satuan=satuan,
                        kuantitas=kuantitas,
                        tgl_masuk=tgl_masuk,
                        status=status,
                        catatan=catatan,
                        nama_lab=nama_lab,
                        total_digunakan=0,
                        sedang_dipakai=0,
                        rusak=0
                    )
                    db.session.add(a)

            # === IMPOR KEJADIAN ===
            if 'Kejadian' in xls.sheet_names:
                df_kejadian = pd.read_excel(xls, 'Kejadian')
                for _, row in df_kejadian.iterrows():
                    tanggal_kejadian = pd.to_datetime(row['tanggal_kejadian']).date()
                    nama_guru = str(row['nama_guru']).strip()
                    kelas = str(row['kelas']).strip()
                    sesi = str(row['sesi']).strip()
                    alat_id = int(row['alat_id'])
                    kuantitas_rusak = int(row['kuantitas_rusak'])
                    deskripsi = str(row['deskripsi']).strip() if 'deskripsi' in row else ''
                    status = str(row['status']).strip() if 'status' in row else 'belum ditangani'
                    nama_lab = str(row['nama_lab']).strip() if 'nama_lab' in row else 'Fisika'

                    if not nama_guru or not kelas or not sesi:
                        flash(f'[Kejadian] Baris {_+1}: Nama Guru, Kelas, dan Sesi wajib diisi.', 'danger')
                        continue
                    if kuantitas_rusak <= 0:
                        flash(f'[Kejadian] Baris {_+1}: Kuantitas Rusak harus lebih dari 0.', 'danger')
                        continue
                    if not Alat.query.get(alat_id):
                        flash(f'[Kejadian] Baris {_+1}: Alat ID {alat_id} tidak ditemukan.', 'danger')
                        continue

                    k = Kejadian(
                        tanggal_kejadian=tanggal_kejadian,
                        nama_guru=nama_guru,
                        kelas=kelas,
                        sesi=sesi,
                        alat_id=alat_id,
                        kuantitas_rusak=kuantitas_rusak,
                        deskripsi=deskripsi,
                        status=status,
                        nama_lab=nama_lab
                    )
                    db.session.add(k)

                    # Sinkronisasi: Update status alat
                    alat = Alat.query.get(alat_id)
                    if alat and alat.status != 'rusak':
                        alat.status = 'rusak'
                        alat.rusak += kuantitas_rusak

            db.session.commit()
            flash('Data berhasil diimpor dari semua sheet!', 'success')
            delete_file_after_delay(filepath, delay=5.0)
            return redirect(url_for('admin_index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error impor: {str(e)}', 'danger')
            if os.path.exists(filepath):
                os.remove(filepath)
    return render_template('admin/upload_all.html')


# --- JALANKAN APLIKASI ---
# --- JADWALKAN PENGECEKAN EXPIRED SECARA BERKALA ---
def schedule_expired_check():
    """Jalankan pengecekan expired setiap jam."""
    while True:
        try:
            with app.app_context():
                check_and_update_expired_bahan()
        except Exception as e:
            print(f"❌ Error saat menjalankan pengecekan expired: {e}")
        time.sleep(3600)  # Tunggu 1 jam


# app.py



# app.py


@app.route('/laporan/bulanan/perbandingan')
@login_required
def laporan_bulanan_perbandingan():
    """
    Halaman laporan bulanan dengan analisis perbandingan 3 bulan terakhir.
    """
    try:
        # Ambil bulan & tahun dari query string, default bulan ini
        bulan_sekarang = int(request.args.get('bulan', datetime.now().month))
        tahun_sekarang = int(request.args.get('tahun', datetime.now().year))
    except (ValueError, TypeError):
        bulan_sekarang = datetime.now().month
        tahun_sekarang = datetime.now().year

    # Validasi bulan & tahun
    if bulan_sekarang < 1 or bulan_sekarang > 12:
        bulan_sekarang = datetime.now().month
    if tahun_sekarang < 2020 or tahun_sekarang > datetime.now().year + 1:
        tahun_sekarang = datetime.now().year

    # === HITUNG DATA UNTUK 3 BULAN TERAKHIR ===
    data_per_bulan = {}
    for i in range(2, -1, -1): # 2 bulan lalu, 1 bulan lalu, bulan ini
        if bulan_sekarang - i > 0:
            b = bulan_sekarang - i
            t = tahun_sekarang
        else:
            b = 12 + (bulan_sekarang - i)
            t = tahun_sekarang - 1
        
        awal_bulan = date(t, b, 1)
        akhir_bulan = date(t, b, calendar.monthrange(t, b)[1])
        nama_bulan = calendar.month_name[b]
        
        # Hitung data
        total_jadwal = JadwalPenggunaan.query.filter(
            JadwalPenggunaan.tanggal.between(awal_bulan, akhir_bulan)
        ).count()
        
        total_kejadian = Kejadian.query.filter(
            Kejadian.tanggal_kejadian.between(awal_bulan, akhir_bulan)
        ).count()
        
        expired_bahan = Bahan.query.filter(
            Bahan.tgl_expired.between(awal_bulan, akhir_bulan),
            Bahan.status_expired == 'expired'
        ).count()
        
        rusak_alat = Alat.query.filter(
            Alat.tgl_masuk.between(awal_bulan, akhir_bulan),
            Alat.status == 'rusak'
        ).count()
        
        # Kejadian per lab
        kejadian_per_lab = db.session.query(
            Kejadian.nama_lab,
            func.count(Kejadian.id).label('jumlah')
        ).filter(
            Kejadian.tanggal_kejadian.between(awal_bulan, akhir_bulan)
        ).group_by(Kejadian.nama_lab).all()
        
        data_per_bulan[nama_bulan] = {
            'bulan': b,
            'tahun': t,
            'nama_bulan': nama_bulan,
            'total_jadwal': total_jadwal,
            'total_kejadian': total_kejadian,
            'expired_bahan': expired_bahan,
            'rusak_alat': rusak_alat,
            'kejadian_per_lab': {k[0]: k[1] for k in kejadian_per_lab}
        }
    
    # === SIAPKAN DATA UNTUK GRAFIK ===
    # Urutkan berdasarkan tanggal
    sorted_data = sorted(data_per_bulan.values(), key=lambda x: date(x['tahun'], x['bulan'], 1))
    
    # Labels untuk grafik (nama bulan)
    labels = [d['nama_bulan'] for d in sorted_data]
    
    # Data untuk bar chart
    jadwal_data = [d['total_jadwal'] for d in sorted_data]
    kejadian_data = [d['total_kejadian'] for d in sorted_data]
    expired_data = [d['expired_bahan'] for d in sorted_data]
    rusak_data = [d['rusak_alat'] for d in sorted_data]
    
    # Data untuk line chart kejadian per bulan (3 bulan terakhir)
    line_labels = labels
    line_data = kejadian_data
    
    # Data untuk doughnut chart kejadian per lab (bulan ini vs 1 bulan lalu)
    # Misalnya, bandingkan bulan ini dengan 1 bulan lalu
    if len(sorted_data) >= 2:
        bulan_ini = sorted_data[-1]
        bulan_lalu = sorted_data[-2]
        
        # Gabungkan lab dari kedua bulan
        semua_lab = set(bulan_ini['kejadian_per_lab'].keys()).union(set(bulan_lalu['kejadian_per_lab'].keys()))
        
        doughnut_labels = list(semua_lab)
        doughnut_data_bulan_ini = [bulan_ini['kejadian_per_lab'].get(lab, 0) for lab in semua_lab]
        doughnut_data_bulan_lalu = [bulan_lalu['kejadian_per_lab'].get(lab, 0) for lab in semua_lab]
    else:
        doughnut_labels = []
        doughnut_data_bulan_ini = []
        doughnut_data_bulan_lalu = []

    # === KIRIM DATA KE TEMPLATE ===
    return render_template(
        'laporan/bulanan/perbandingan.html',
        bulan_sekarang=bulan_sekarang,
        tahun_sekarang=tahun_sekarang,
        nama_bulan_sekarang=calendar.month_name[bulan_sekarang],
        nama_bulan_list=[calendar.month_name[i] for i in range(1, 13)],
        data_per_bulan=data_per_bulan,
        sorted_data=sorted_data,
        # Data untuk grafik
        labels=labels,
        jadwal_data=jadwal_data,
        kejadian_data=kejadian_data,
        expired_data=expired_data,
        rusak_data=rusak_data,
        line_labels=line_labels,
        line_data=line_data,
        doughnut_labels=doughnut_labels,
        doughnut_data_bulan_ini=doughnut_data_bulan_ini,
        doughnut_data_bulan_lalu=doughnut_data_bulan_lalu
    )

# app.py

# app.py

@app.route('/laporan/bulanan')
@login_required
def laporan_bulanan():
    """Halaman laporan bulanan"""
    try:
        bulan_sekarang = int(request.args.get('bulan', datetime.now().month))
        tahun_sekarang = int(request.args.get('tahun', datetime.now().year))
    except (ValueError, TypeError):
        bulan_sekarang = datetime.now().month
        tahun_sekarang = datetime.now().year

    if bulan_sekarang < 1 or bulan_sekarang > 12:
        bulan_sekarang = datetime.now().month
    if tahun_sekarang < 2020 or tahun_sekarang > datetime.now().year + 1:
        tahun_sekarang = datetime.now().year

    awal_bulan = date(tahun_sekarang, bulan_sekarang, 1)
    akhir_bulan = date(tahun_sekarang, bulan_sekarang, calendar.monthrange(tahun_sekarang, bulan_sekarang)[1])
    nama_bulan_sekarang = calendar.month_name[bulan_sekarang]
    nama_bulan_list = [calendar.month_name[i] for i in range(1, 13)]

    # === HITUNG DATA LAPORAN ===
    
    # --- Bahan ---
    bahan_list = Bahan.query.filter(
        db.or_(
            Bahan.tgl_masuk.between(awal_bulan, akhir_bulan),
            Bahan.tgl_expired.between(awal_bulan, akhir_bulan)
        )
    ).all()
    
    total_bahan = len(bahan_list)
    expired_bahan = Bahan.query.filter(
        Bahan.tgl_expired.between(awal_bulan, akhir_bulan),
        Bahan.status_expired == 'expired'
    ).count()

    # --- Alat ---
    alat_list = Alat.query.filter(
        Alat.tgl_masuk.between(awal_bulan, akhir_bulan)
    ).all()
    
    total_alat = len(alat_list)
    rusak_alat = Alat.query.filter(
        Alat.tgl_masuk.between(awal_bulan, akhir_bulan),
        Alat.status == 'rusak'
    ).count()

    # --- Kejadian ---
    kejadian_list = Kejadian.query.filter(
        Kejadian.tanggal_kejadian.between(awal_bulan, akhir_bulan)
    ).all()

    # --- Berita Acara ---
    berita_acara_list = BeritaAcara.query.filter(
        BeritaAcara.tanggal.between(awal_bulan, akhir_bulan)
    ).all()

    # === UPDATE COUNTDOWN UNTUK BAHAN EXPIRED ===
    for b in bahan_list:
        b.countdown_str = None
        b.countdown_seconds = 0

        if b.tgl_expired and b.status_expired == 'belum expired':
            try:
                expiry_datetime = datetime.combine(b.tgl_expired, datetime.min.time())
                now_datetime = datetime.now()
                diff = expiry_datetime - now_datetime
                if diff.total_seconds() > 0:
                    days = diff.days
                    hours, remainder = divmod(diff.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    b.countdown_str = f"{days}d {hours}h {minutes}m {seconds}s"
                    b.countdown_seconds = int(diff.total_seconds())
                else:
                    # Jika sudah lewat, update status expired
                    b.status_expired = 'expired'
                    acara = BeritaAcara(
                        tanggal=datetime.now().date(),
                        jenis='bahan',
                        item_id=b.id,
                        nama_item=b.nama_bahan,
                        alasan='Expired',
                        keterangan=f'Bahan {b.nama_bahan} (Kode: {b.kode}) telah melewati tanggal kadaluarsa ({b.tgl_expired}).',
                        nama_petugas='Sistem Otomatis'
                    )
                    db.session.add(acara)
            except Exception as e:
                print(f"Error menghitung countdown untuk bahan {b.id}: {str(e)}")
                b.countdown_str = "Error"
                b.countdown_seconds = 0

    db.session.commit()

    return render_template(
        'laporan/bulanan.html',
        bulan_sekarang=bulan_sekarang,
        tahun_sekarang=tahun_sekarang,
        nama_bulan_sekarang=nama_bulan_sekarang,
        nama_bulan_list=nama_bulan_list,
        bahan_list=bahan_list,
        alat_list=alat_list,
        kejadian_list=kejadian_list,
        berita_acara_list=berita_acara_list,
        total_bahan=total_bahan,
        expired_bahan=expired_bahan,
        total_alat=total_alat,
        rusak_alat=rusak_alat
    )

# app.py

from flask import send_file
from datetime import datetime, date
import io
import calendar
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape

@app.route('/laporan/bulanan/download/pdf')
@login_required
def download_laporan_pdf():
    """
    Download laporan bulanan dalam format PDF dengan opsi orientasi.
    """
    try:
        bulan = int(request.args.get('bulan', datetime.now().month))
        tahun = int(request.args.get('tahun', datetime.now().year))
        orientasi = request.args.get('orientasi', 'portrait').lower()
    except (ValueError, TypeError):
        bulan = datetime.now().month
        tahun = datetime.now().year
        orientasi = 'portrait'

    # Validasi bulan & tahun
    if bulan < 1 or bulan > 12:
        bulan = datetime.now().month
    if tahun < 2020 or tahun > datetime.now().year + 1:
        tahun = datetime.now().year
    if orientasi not in ['portrait', 'landscape']:
        orientasi = 'portrait'

    awal_bulan = date(tahun, bulan, 1)
    akhir_bulan = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])
    nama_bulan = calendar.month_name[bulan]

    # === HITUNG DATA UNTUK LAPORAN ===
    
    # --- Jadwal Penggunaan ---
    total_jadwal = JadwalPenggunaan.query.filter(
        JadwalPenggunaan.tanggal.between(awal_bulan, akhir_bulan)
    ).count()
    
    jadwal_per_lab = db.session.query(
        JadwalPenggunaan.nama_lab,
        func.count(JadwalPenggunaan.id).label('jumlah')
    ).filter(
        JadwalPenggunaan.tanggal.between(awal_bulan, akhir_bulan)
    ).group_by(JadwalPenggunaan.nama_lab).all()
    
    # --- Bahan Digunakan ---
    bahan_digunakan = db.session.query(
        Bahan.nama_bahan,
        Bahan.satuan,
        func.sum(JadwalBahan.kuantitas_digunakan).label('total_digunakan')
    ).join(JadwalBahan, Bahan.id == JadwalBahan.bahan_id)\
     .join(JadwalPenggunaan, JadwalBahan.jadwal_id == JadwalPenggunaan.id)\
     .filter(JadwalPenggunaan.tanggal.between(awal_bulan, akhir_bulan))\
     .group_by(Bahan.id, Bahan.nama_bahan, Bahan.satuan)\
     .order_by(func.sum(JadwalBahan.kuantitas_digunakan).desc()).all()
    
    # --- Alat Digunakan ---
    alat_digunakan = db.session.query(
        Alat.nama_alat,
        Alat.satuan,
        func.sum(JadwalAlat.kuantitas_digunakan).label('total_digunakan')
    ).join(JadwalAlat, Alat.id == JadwalAlat.alat_id)\
     .join(JadwalPenggunaan, JadwalAlat.jadwal_id == JadwalPenggunaan.id)\
     .filter(JadwalPenggunaan.tanggal.between(awal_bulan, akhir_bulan))\
     .group_by(Alat.id, Alat.nama_alat, Alat.satuan)\
     .order_by(func.sum(JadwalAlat.kuantitas_digunakan).desc()).all()
    
    # --- Kejadian ---
    total_kejadian = Kejadian.query.filter(
        Kejadian.tanggal_kejadian.between(awal_bulan, akhir_bulan)
    ).count()
    
    kejadian_per_lab = db.session.query(
        Kejadian.nama_lab,
        func.count(Kejadian.id).label('jumlah')
    ).filter(
        Kejadian.tanggal_kejadian.between(awal_bulan, akhir_bulan)
    ).group_by(Kejadian.nama_lab).all()
    
    # --- Alat Rusak ---
    alat_rusak_list = db.session.query(
        Alat.nama_alat,
        func.sum(Kejadian.kuantitas_rusak).label('total_rusak')
    ).join(Kejadian, Alat.id == Kejadian.alat_id)\
     .filter(Kejadian.tanggal_kejadian.between(awal_bulan, akhir_bulan))\
     .group_by(Alat.id, Alat.nama_alat)\
     .order_by(func.sum(Kejadian.kuantitas_rusak).desc()).all()
    
    # --- Bahan Expired ---
    bahan_expired = Bahan.query.filter(
        Bahan.tgl_expired.between(awal_bulan, akhir_bulan),
        Bahan.status_expired == 'expired'
    ).all()

    # --- Statistik Umum ---
    total_bahan = Bahan.query.count()
    # ✅ Perbaiki: Hitung bahan habis dengan ekspresi kolom
    bahan_habis = db.session.query(func.count(Bahan.id)).filter(
        (Bahan.kuantitas - Bahan.total_digunakan) <= 0
    ).scalar() or 0
    total_alat = Alat.query.count()
    # ✅ Perbaiki: Hitung alat rusak dengan status
    alat_rusak = Alat.query.filter_by(status='rusak').count()

    # === DATA DETAIL UNTUK LAPORAN ===
    
    # --- Bahan Detail (nama bahan, kuantitas, tgl expired, total digunakan) ---
    bahan_detail = db.session.query(
        Bahan.nama_bahan,
        Bahan.kuantitas.label('stok_awal'),
        Bahan.satuan,
        Bahan.tgl_expired,
        func.coalesce(func.sum(JadwalBahan.kuantitas_digunakan), 0).label('total_digunakan')
    ).outerjoin(JadwalBahan, Bahan.id == JadwalBahan.bahan_id)\
     .outerjoin(JadwalPenggunaan, JadwalBahan.jadwal_id == JadwalPenggunaan.id)\
     .filter(
        db.or_(
            JadwalPenggunaan.tanggal.between(awal_bulan, akhir_bulan),
            Bahan.tgl_expired.between(awal_bulan, akhir_bulan)
        )
     ).group_by(Bahan.id, Bahan.nama_bahan, Bahan.kuantitas, Bahan.satuan, Bahan.tgl_expired).all()

    # --- Alat Detail (status, catatan) ---
    # Filter alat yang statusnya berubah atau ada kejadian di bulan ini
    alat_ids_with_incident = db.session.query(Kejadian.alat_id).filter(
        Kejadian.tanggal_kejadian.between(awal_bulan, akhir_bulan)
    ).subquery()
    
    alat_detail = Alat.query.filter(
        db.or_(
            Alat.status.in_(['rusak']),
            Alat.id.in_(alat_ids_with_incident)
        )
    ).all()

    # --- Kejadian Detail ---
    kejadian_detail = Kejadian.query.filter(
        Kejadian.tanggal_kejadian.between(awal_bulan, akhir_bulan)
    ).all()

    # --- Berita Acara Detail ---
    # Filter berita acara yang dibuat di bulan ini (bukan yang terkait kejadian/expired)
    berita_acara_detail = BeritaAcara.query.filter(
        BeritaAcara.tanggal.between(awal_bulan, akhir_bulan)
    ).all()

    # === BUAT PDF ===
    buffer = io.BytesIO()
    # ✅ Gunakan orientasi yang dipilih
    pagesize = A4 if orientasi == 'portrait' else landscape(A4)
    doc = SimpleDocTemplate(buffer, pagesize=pagesize)
    elements = []
    styles = getSampleStyleSheet()
    
    # Style khusus untuk judul
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    # ✅ Tambahkan tanggal & waktu generate
    waktu_generate = datetime.now().strftime("%d %b %Y, %H:%M:%S")
    
    # Judul
    title = Paragraph(
        f"Laporan Bulanan Laboratorium<br/>{nama_bulan} {tahun}<br/>"
        f"<font size='10'><i>Digenerate pada: {waktu_generate}</i></font>",
        title_style
    )
    elements.append(title)
    elements.append(Spacer(1, 12))

    # === FUNGSI PEMBANTU UNTUK MEMBUAT TABEL RAPI ===
    def buat_tabel_rapi(data, headers, col_widths=None):
        """Helper untuk membuat tabel dengan styling rapi."""
        table_data = [headers] + data
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8), # Ukuran font kecil agar muat
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return table

    # === ISI LAPORAN ===
    
    # Ringkasan Kartu
    ringkasan_data = [
        ['Total Bahan', str(total_bahan)],
        ['Total Alat', str(total_alat)],
        ['Bahan Expired', str(len(bahan_expired))],
        ['Alat Rusak', str(alat_rusak)],
        ['Total Jadwal', str(total_jadwal)],
        ['Total Kejadian', str(total_kejadian)]
    ]
    ringkasan_table = buat_tabel_rapi(ringkasan_data, ['Indikator', 'Jumlah'])
    elements.append(Paragraph("Ringkasan Statistik", styles['Heading2']))
    elements.append(ringkasan_table)
    elements.append(Spacer(1, 12))

    # Jadwal Penggunaan per Lab
    if jadwal_per_lab:
        jadwal_data = [[lab, str(jumlah)] for lab, jumlah in jadwal_per_lab]
        jadwal_table = buat_tabel_rapi(
            jadwal_data,
            ['Lab', 'Jumlah Jadwal'],
            col_widths=[2*inch, 1.5*inch]
        )
        elements.append(Paragraph("Jadwal Penggunaan per Lab", styles['Heading2']))
        elements.append(jadwal_table)
        elements.append(Spacer(1, 12))

    # Bahan Digunakan
    if bahan_digunakan:
        bahan_digunakan_data = [[b.nama_bahan, b.satuan, f"{b.total_digunakan:.2f}"] for b in bahan_digunakan]
        bahan_digunakan_table = buat_tabel_rapi(
            bahan_digunakan_data,
            ['Nama Bahan', 'Satuan', 'Total Digunakan'],
            col_widths=[2*inch, 1*inch, 1.5*inch]
        )
        elements.append(Paragraph("Bahan yang Digunakan", styles['Heading2']))
        elements.append(bahan_digunakan_table)
        elements.append(Spacer(1, 12))

    # Alat Digunakan
    if alat_digunakan:
        alat_digunakan_data = [[a.nama_alat, a.satuan, f"{a.total_digunakan:.2f}"] for a in alat_digunakan]
        alat_digunakan_table = buat_tabel_rapi(
            alat_digunakan_data,
            ['Nama Alat', 'Satuan', 'Total Digunakan'],
            col_widths=[2*inch, 1*inch, 1.5*inch]
        )
        elements.append(Paragraph("Alat yang Digunakan", styles['Heading2']))
        elements.append(alat_digunakan_table)
        elements.append(Spacer(1, 12))

    # Kejadian per Lab
    if kejadian_per_lab:
        kejadian_data = [[lab, str(jumlah)] for lab, jumlah in kejadian_per_lab]
        kejadian_table = buat_tabel_rapi(
            kejadian_data,
            ['Lab', 'Jumlah Kejadian'],
            col_widths=[2*inch, 1.5*inch]
        )
        elements.append(Paragraph("Kejadian per Lab", styles['Heading2']))
        elements.append(kejadian_table)
        elements.append(Spacer(1, 12))

    # Bahan Expired
    if bahan_expired:
        expired_data = [[b.kode, b.nama_bahan, b.tgl_expired.strftime('%d %b %Y')] for b in bahan_expired]
        expired_table = buat_tabel_rapi(
            expired_data,
            ['Kode', 'Nama Bahan', 'Tanggal Expired'],
            col_widths=[1*inch, 2*inch, 1.5*inch]
        )
        elements.append(Paragraph("Bahan yang Expired", styles['Heading2']))
        elements.append(expired_table)
        elements.append(Spacer(1, 12))

    # Alat Rusak
    if alat_rusak_list:
        rusak_data = [[nama, str(int(total_rusak))] for nama, total_rusak in alat_rusak_list]
        rusak_table = buat_tabel_rapi(
            rusak_data,
            ['Nama Alat', 'Jumlah Rusak'],
            col_widths=[2*inch, 1.5*inch]
        )
        elements.append(Paragraph("Alat yang Rusak", styles['Heading2']))
        elements.append(rusak_table)
        elements.append(Spacer(1, 12))

    # === DATA DETAIL ===

    # Detail Bahan
    if bahan_detail:
        detail_bahan_data = []
        for b in bahan_detail:
            detail_bahan_data.append([
                b.nama_bahan,
                f"{b.stok_awal:.2f} {b.satuan}",
                b.tgl_expired.strftime('%d %b %Y') if b.tgl_expired else '-',
                f"{float(b.total_digunakan):.2f} {b.satuan}"
            ])
        detail_bahan_table = buat_tabel_rapi(
            detail_bahan_data,
            ['Nama Bahan', 'Stok Awal', 'Tanggal Expired', 'Total Digunakan'],
            col_widths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch]
        )
        elements.append(Paragraph("Detail Bahan (Stok & Penggunaan)", styles['Heading2']))
        elements.append(detail_bahan_table)
        elements.append(Spacer(1, 12))

    # Detail Alat
    if alat_detail:
        detail_alat_data = []
        for a in alat_detail:
            detail_alat_data.append([
                a.kode,
                a.nama_alat,
                a.kuantitas,
                a.sedang_dipakai,
                a.rusak,
                a.tersedia_baik,
                a.status,
                a.catatan or '-'
            ])
        detail_alat_table = buat_tabel_rapi(
            detail_alat_data,
            ['Kode', 'Nama Alat', 'Kuantitas', 'Sedang Dipakai', 'Rusak', 'Tersedia Baik', 'Status', 'Catatan'],
            col_widths=[0.8*inch, 1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.5*inch]
        )
        elements.append(Paragraph("Detail Alat (Status & Catatan)", styles['Heading2']))
        elements.append(detail_alat_table)
        elements.append(Spacer(1, 12))

    # === PERBAIKAN: Detail Kejadian dengan Paragraph & KeepTogether ===
    if kejadian_detail:
        detail_kejadian_data = []
        for k in kejadian_detail:
            detail_kejadian_data.append([
                k.tanggal_kejadian.strftime('%d %b %Y'),
                k.nama_guru,
                k.kelas,
                k.sesi,
                k.alat.nama_alat if k.alat else 'Tidak Diketahui',
                str(k.kuantitas_rusak),
                Paragraph(k.deskripsi or '-', styles['Normal']),  # ✅ Gunakan Paragraph
                k.status
            ])
        
        # Buat tabel dengan KeepTogether untuk mencegah split halaman
        detail_kejadian_table = buat_tabel_rapi(
            detail_kejadian_data,
            ['Tanggal', 'Guru', 'Kelas', 'Sesi', 'Alat', 'Rusak', 'Deskripsi', 'Status'],
            col_widths=[1*inch, 1*inch, 0.8*inch, 0.8*inch, 1.5*inch, 0.5*inch, 1.5*inch, 0.8*inch]
        )
        
        elements.append(Paragraph("Detail Kejadian", styles['Heading2']))
        elements.append(KeepTogether([detail_kejadian_table]))  # ✅ Gunakan KeepTogether
        elements.append(Spacer(1, 12))

    # === PERBAIKAN: Detail Berita Acara dengan Paragraph & KeepTogether ===
    if berita_acara_detail:
        detail_ba_data = []
        for ba in berita_acara_detail:
            detail_ba_data.append([
                ba.tanggal.strftime('%d %b %Y'),
                ba.jenis.title(),
                ba.nama_item,
                ba.alasan,
                Paragraph(ba.keterangan or '-', styles['Normal']),  # ✅ Gunakan Paragraph
                ba.nama_petugas,
                ba.status_follow_up or 'Belum Ditangani',
                str(ba.kuantitas_tindakan or 0),
                ba.tanggal_tindakan.strftime('%d %b %Y') if ba.tanggal_tindakan else '-',
                Paragraph(ba.catatan_tindakan or '-', styles['Normal'])  # ✅ Gunakan Paragraph
            ])
        
        # Buat tabel dengan KeepTogether untuk mencegah split halaman
        detail_ba_table = buat_tabel_rapi(
            detail_ba_data,
            ['Tanggal', 'Jenis', 'Nama Item', 'Alasan', 'Keterangan', 'Petugas', 'Status FU', 'Qty Tindakan', 'Tgl Tindakan', 'Catatan Tindakan'],
            col_widths=[1*inch, 0.8*inch, 1.2*inch, 0.8*inch, 1.2*inch, 1*inch, 1*inch, 0.6*inch, 1*inch, 1.2*inch]
        )
        
        elements.append(Paragraph("Detail Berita Acara", styles['Heading2']))
        elements.append(KeepTogether([detail_ba_table]))  # ✅ Gunakan KeepTogether
        elements.append(Spacer(1, 12))

    # Bangun PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Nama file
    filename = f"laporan_bulanan_{nama_bulan}_{tahun}_{orientasi}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


@app.route('/laporan/bulanan/download/xlsx')
@login_required
def download_laporan_xlsx():
    """Download laporan bulanan dalam format Excel"""
    try:
        bulan = int(request.args.get('bulan', datetime.now().month))
        tahun = int(request.args.get('tahun', datetime.now().year))
    except (ValueError, TypeError):
        bulan = datetime.now().month
        tahun = datetime.now().year

    if bulan < 1 or bulan > 12:
        bulan = datetime.now().month
    if tahun < 2020 or tahun > datetime.now().year + 1:
        tahun = datetime.now().year

    awal_bulan = date(tahun, bulan, 1)
    akhir_bulan = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])
    nama_bulan = calendar.month_name[bulan]

    # === DATA UNTUK XLSX ===
    # ... (semua query seperti di route /laporan/bulanan) ...
    
    # --- Bahan Detail ---
    bahan_detail = db.session.query(
        Bahan.nama_bahan,
        Bahan.kuantitas.label('stok_awal'),
        Bahan.satuan,
        Bahan.tgl_expired,
        func.coalesce(func.sum(JadwalBahan.kuantitas_digunakan), 0).label('total_digunakan')
    ).outerjoin(JadwalBahan, Bahan.id == JadwalBahan.bahan_id)\
     .outerjoin(JadwalPenggunaan, JadwalBahan.jadwal_id == JadwalPenggunaan.id)\
     .filter(
        db.or_(
            JadwalPenggunaan.tanggal.between(awal_bulan, akhir_bulan),
            Bahan.tgl_expired.between(awal_bulan, akhir_bulan)
        )
     ).group_by(Bahan.id).all()

    # --- Alat Detail ---
    alat_ids_with_incident = db.session.query(Kejadian.alat_id).filter(
        Kejadian.tanggal_kejadian.between(awal_bulan, akhir_bulan)
    ).subquery()
    alat_detail = Alat.query.filter(
        db.or_(
            Alat.status.in_(['rusak']),
            Alat.id.in_(alat_ids_with_incident)
        )
    ).all()

    # --- Kejadian Detail ---
    kejadian_detail = Kejadian.query.filter(
        Kejadian.tanggal_kejadian.between(awal_bulan, akhir_bulan)
    ).all()

    # --- Berita Acara Detail ---
    berita_acara_detail = BeritaAcara.query.filter(
        BeritaAcara.tanggal.between(awal_bulan, akhir_bulan)
    ).all()

    # Buat file Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Statistik Umum
        stats_df = pd.DataFrame({
            'Statistik': [
                'Total Jadwal', 
                'Total Kejadian', 
                'Total Bahan', 
                'Total Alat', 
                'Alat Rusak'
            ],
            'Jumlah': [
                JadwalPenggunaan.query.filter(
                    JadwalPenggunaan.tanggal.between(awal_bulan, akhir_bulan)
                ).count(),
                Kejadian.query.filter(
                    Kejadian.tanggal_kejadian.between(awal_bulan, akhir_bulan)
                ).count(),
                Bahan.query.count(),
                Alat.query.count(),
                Alat.query.filter_by(status='rusak').count()
            ]
        })
        stats_df.to_excel(writer, sheet_name='Statistik', index=False)

        # Sheet 2: Bahan Detail
        if bahan_detail:
            bahan_detail_data = []
            for b in bahan_detail:
                bahan_detail_data.append({
                    'Nama Bahan': b.nama_bahan,
                    'Stok Awal': f"{b.stok_awal:.2f} {b.satuan}",
                    'Tanggal Expired': b.tgl_expired.strftime('%d %b %Y') if b.tgl_expired else '-',
                    'Total Digunakan': f"{float(b.total_digunakan):.2f} {b.satuan}"
                })
            pd.DataFrame(bahan_detail_data).to_excel(writer, sheet_name='Detail Bahan', index=False)

        # Sheet 3: Alat Detail
        if alat_detail:
            alat_detail_data = []
            for a in alat_detail:
                alat_detail_data.append({
                    'Kode': a.kode,
                    'Nama Alat': a.nama_alat,
                    'Status': a.status,
                    'Catatan': a.catatan or '-'
                })
            pd.DataFrame(alat_detail_data).to_excel(writer, sheet_name='Detail Alat', index=False)

        # Sheet 4: Kejadian Detail
        if kejadian_detail:
            kejadian_detail_data = []
            for k in kejadian_detail:
                kejadian_detail_data.append({
                    'Tanggal': k.tanggal_kejadian.strftime('%d %b %Y'),
                    'Guru': k.nama_guru,
                    'Kelas': k.kelas,
                    'Alat': k.alat.nama_alat if k.alat else 'Tidak Diketahui',
                    'Rusak': k.kuantitas_rusak,
                    'Deskripsi': k.deskripsi or '-',
                    'Status': k.status
                })
            pd.DataFrame(kejadian_detail_data).to_excel(writer, sheet_name='Detail Kejadian', index=False)

        # Sheet 5: Berita Acara Detail
        if berita_acara_detail:
            ba_detail_data = []
            for ba in berita_acara_detail:
                ba_detail_data.append({
                    'Tanggal': ba.tanggal.strftime('%d %b %Y'),
                    'Jenis': ba.jenis.title(),
                    'Nama Item': ba.nama_item,
                    'Alasan': ba.alasan,
                    'Keterangan': ba.keterangan or '-',
                    'Petugas': ba.nama_petugas,
                    'Status Follow Up': ba.status_follow_up or 'Belum Ditangani',
                    'Kuantitas Tindakan': ba.kuantitas_tindakan or 0,
                    'Tanggal Tindakan': ba.tanggal_tindakan.strftime('%d %b %Y') if ba.tanggal_tindakan else '-',
                    'Catatan Tindakan': ba.catatan_tindakan or '-'
                })
            pd.DataFrame(ba_detail_data).to_excel(writer, sheet_name='Detail Berita Acara', index=False)

    output.seek(0)
    
    # Nama file
    filename = f"laporan_bulanan_{nama_bulan}_{tahun}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )




# app.py

if __name__ == '__main__':
    import threading
    expired_thread = threading.Thread(target=schedule_expired_check, daemon=True)
    expired_thread.start()

    with app.app_context():
        db.create_all()
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        static_uploads_folder = os.path.join(app.static_folder, 'uploads')
        os.makedirs(static_uploads_folder, exist_ok=True)

    # Use the PORT environment variable provided by Railway
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
