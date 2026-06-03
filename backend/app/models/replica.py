from app import db
from datetime import datetime, timezone


class Replica(db.Model):
    __tablename__ = "replicas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    origen_id = db.Column(db.Integer, db.ForeignKey("bases_datos.id"), nullable=False)
    destino_id = db.Column(db.Integer, db.ForeignKey("bases_datos.id"), nullable=False)
    tipo = db.Column(db.String(50), default="COMPLETA")
    frecuencia = db.Column(db.String(50), default="MANUAL")
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    estado = db.Column(db.String(50), default="PENDIENTE")
    filas_afectadas = db.Column(db.Integer, default=0)
    duracion_segundos = db.Column(db.Float)
    detalle = db.Column(db.Text)
    usuario = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    origen = db.relationship("BaseDatos", foreign_keys=[origen_id])
    destino = db.relationship("BaseDatos", foreign_keys=[destino_id])
