from app import db
from datetime import datetime, timezone


class Schedule(db.Model):
    __tablename__ = "horarios"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # BACKUP / REPLICA
    id_bd = db.Column(db.Integer, db.ForeignKey("bases_datos.id"))
    id_origen = db.Column(db.Integer, db.ForeignKey("bases_datos.id"))
    id_destino = db.Column(db.Integer, db.ForeignKey("bases_datos.id"))
    formato = db.Column(db.String(20), default="custom")
    compresion = db.Column(db.String(10))
    cron_minuto = db.Column(db.String(10), default="0")
    cron_hora = db.Column(db.String(10), default="*")
    cron_dia = db.Column(db.String(10), default="*")
    cron_mes = db.Column(db.String(10), default="*")
    cron_semana = db.Column(db.String(10), default="*")
    activo = db.Column(db.Boolean, default=True)
    ultima_ejecucion = db.Column(db.DateTime)
    ejecutando = db.Column(db.Boolean, default=False)
    ultimo_resultado = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
