from app import db
from datetime import datetime, timezone


class Servidor(db.Model):
    __tablename__ = "servidores"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(200), nullable=False)
    host = db.Column(db.String(100), nullable=False)
    puerto = db.Column(db.Integer, default=22)
    usuario_ssh = db.Column(db.String(100))
    clave_ssh = db.Column(db.Text)
    ruta_backups = db.Column(db.Text)
    tipo = db.Column(db.String(50), default="ORIGEN")
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    bases_datos = db.relationship("BaseDatos", backref="servidor", lazy="dynamic")
