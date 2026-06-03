from app import db
from datetime import datetime, timezone


class Restauracion(db.Model):
    __tablename__ = "restauraciones"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    backup_id = db.Column(db.Integer, db.ForeignKey("backups.id"), nullable=False)
    servidor_id = db.Column(db.Integer, db.ForeignKey("servidores.id"), nullable=False)
    base_datos_id = db.Column(db.Integer, db.ForeignKey("bases_datos.id"))
    usuario = db.Column(db.String(100))
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    estado = db.Column(db.String(50), default="PENDIENTE")
    detalle = db.Column(db.Text)
    duracion_segundos = db.Column(db.Float)

    backup = db.relationship("Backup", backref="restauraciones")
    servidor = db.relationship("Servidor", backref="restauraciones")
