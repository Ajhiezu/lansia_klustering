"""
Dua tabel:
  - upload_batch   : metadata setiap kali file Excel diupload
  - lansia_record  : data individu lansia hasil preprocessing (1 baris = 1 orang)
"""
from datetime import datetime
from app.extensions import db


class UploadBatch(db.Model):
    __tablename__ = "upload_batch"

    id          = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    filename    = db.Column(db.String(255), nullable=False)
    bulan       = db.Column(db.String(30),  nullable=True)   # "Januari 2026"
    uploaded_at = db.Column(db.DateTime,    default=datetime.utcnow)
    total_rows  = db.Column(db.Integer,     default=0)
    total_desa  = db.Column(db.Integer,     default=0)
    status      = db.Column(db.String(20),  default="success")
    stats_json  = db.Column(db.JSON,        nullable=True)

    records = db.relationship(
        "LansiaRecord",
        backref="batch",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<UploadBatch id={self.id} | {self.filename} | {self.total_rows} baris>"


class LansiaRecord(db.Model):
    __tablename__ = "lansia_record"

    # ── Key ──
    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_id = db.Column(
        db.Integer,
        db.ForeignKey("upload_batch.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # ── Identitas ──
    desa          = db.Column(db.String(100), nullable=False, index=True)
    nama          = db.Column(db.String(150), nullable=False)
    nik           = db.Column(db.String(20),  nullable=True,  index=True)

    # ── Demografi ──
    umur          = db.Column(db.Float, nullable=True)
    jenis_kelamin = db.Column(db.Float, nullable=True)   # 1=L, 0=P

    # ── Kunjungan ──
    kunjungan_baru = db.Column(db.Float, default=0.0)
    kunjungan_lama = db.Column(db.Float, default=0.0)

    # ── IMT ──
    imt = db.Column(db.Float, nullable=True)

    # ── Tekanan Darah ──
    sistol  = db.Column(db.Float,    nullable=True)
    diastol = db.Column(db.Float,    nullable=True)

    # ── Lab ──
    hb           = db.Column(db.Float, nullable=True)
    kolesterol   = db.Column(db.Float, nullable=True)
    gula_darah   = db.Column(db.Float, nullable=True)
    asam_urat    = db.Column(db.Float, nullable=True)

    # ── Kemandirian ──
    kemandirian_A        = db.Column(db.Float,   default=0.0)
    kemandirian_B        = db.Column(db.Float,   default=0.0)

    # ── SKILAS ──
    skilas_penurunan_kognitif     = db.Column(db.Float, default=0.0)
    skilas_keterbatasan_mobilitas = db.Column(db.Float, default=0.0)
    skilas_malnutrisi             = db.Column(db.Float, default=0.0)
    skilas_ggn_penglihatan        = db.Column(db.Float, default=0.0)
    skilas_ggn_pendengaran        = db.Column(db.Float, default=0.0)
    skilas_gejala_depresi         = db.Column(db.Float, default=0.0)

    # ── Gangguan ──
    gangguan_paru          = db.Column(db.Float, default=0.0)
    gangguan_ginjal        = db.Column(db.Float, default=0.0)

    # ── Tindakan ──
    diobati  = db.Column(db.Float, default=0.0)
    dirujuk  = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LansiaRecord {self.nama} | {self.desa}>"

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
