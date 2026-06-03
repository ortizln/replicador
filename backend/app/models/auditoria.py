from app import db
from datetime import datetime, timezone


class Auditoria(db.Model):
    __tablename__ = "auditoria_general"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario = db.Column(db.String(100), nullable=False)
    ip = db.Column(db.String(45))
    accion = db.Column(db.String(200), nullable=False)
    entidad = db.Column(db.String(100))
    entidad_id = db.Column(db.Integer)
    detalle = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
