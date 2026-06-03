from app import db
from datetime import datetime, timezone


class Config(db.Model):
    __tablename__ = "configuracion"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    clave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
