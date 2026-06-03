from app import db
from datetime import datetime, timezone


class Log(db.Model):
    __tablename__ = "logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    nivel = db.Column(db.String(20), default="INFO")
    servicio = db.Column(db.String(100))
    codigo = db.Column(db.String(50))
    mensaje = db.Column(db.Text)
    detalle = db.Column(db.Text)
    id_servidor = db.Column(db.Integer, db.ForeignKey("servidores.id"))
    id_backup = db.Column(db.Integer, db.ForeignKey("backups.id"))
    id_replica = db.Column(db.Integer, db.ForeignKey("replicas.id"))
    usuario = db.Column(db.String(100))
    ip_origen = db.Column(db.String(45))
