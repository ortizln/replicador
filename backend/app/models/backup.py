from app import db
from datetime import datetime, timezone


class Backup(db.Model):
    __tablename__ = "backups"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_bd = db.Column(db.Integer, db.ForeignKey("bases_datos.id"), nullable=False)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    tipo = db.Column(db.String(50), default="COMPLETO")
    formato = db.Column(db.String(20), default=".dump")
    compresion = db.Column(db.String(10))
    archivo = db.Column(db.Text, nullable=False)
    peso_bytes = db.Column(db.Integer)
    hash_sha256 = db.Column(db.String(64))
    hash_verificado = db.Column(db.Boolean, default=False)
    estado = db.Column(db.String(50), default="PENDIENTE")
    destino_externo = db.Column(db.String(100))
    transferido = db.Column(db.Boolean, default=False)
    usuario = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    base_datos = db.relationship("BaseDatos", backref="backups")
