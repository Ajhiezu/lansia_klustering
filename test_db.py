from app import create_app
from app.extensions import db
from app.services.db_service import get_all_batches, get_summary

app = create_app()
with app.app_context():

    # 1. Cek koneksi
    try:
        db.session.execute(db.text("SELECT 1"))
        print("[SUCCESS] Koneksi MySQL Laragon berhasil")
    except Exception as e:
        print(f"[ERROR] Gagal koneksi: {e}")
        exit()

    # 2. Cek tabel
    from sqlalchemy import inspect
    tables = inspect(db.engine).get_table_names()
    print(f"[INFO] Tabel di database: {tables}")

    # 3. Cek data (jika sudah pernah upload)
    batches = get_all_batches()
    if batches:
        b = batches[0]
        print(f"[SUCCESS] Batch terbaru : {b.filename} ({b.bulan})")
        print(f"   Total lansia  : {b.total_rows}")
        print(f"   Total desa    : {b.total_desa}")
        print(f"   Upload pada   : {b.uploaded_at}")
        stats = get_summary(b.id)
        print(f"   Distribusi JK : {stats.get('jk')}")
    else:
        print("[INFO] Belum ada data. Silakan upload file Excel terlebih dahulu.")
