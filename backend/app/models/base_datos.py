from app import db
from datetime import datetime, timezone


class BaseDatos(db.Model):
    __tablename__ = "bases_datos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_servidor = db.Column(db.Integer, db.ForeignKey("servidores.id"), nullable=False)
    motor = db.Column(db.String(50), nullable=False)
    nombre_bd = db.Column(db.String(200), nullable=False)
    host = db.Column(db.String(100))
    puerto = db.Column(db.Integer)
    usuario_bd = db.Column(db.String(100))
    password_bd = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
