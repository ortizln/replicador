from datetime import datetime, timedelta
from app.models.backup import Backup
from app.models.replica import Replica
from app.models.log import Log
from app.models.restauracion import Restauracion
from app import db


class MonitoringService:

    @staticmethod
    def obtener_estado_general() -> dict:
        hoy = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        manana = hoy + timedelta(days=1)

        backups_hoy = Backup.query.filter(
            Backup.fecha >= hoy, Backup.fecha < manana
        ).count()
        backups_exitosos_hoy = Backup.query.filter(
            Backup.fecha >= hoy, Backup.fecha < manana,
            Backup.estado == "EXITOSO"
        ).count()
        backups_fallidos_hoy = Backup.query.filter(
            Backup.fecha >= hoy, Backup.fecha < manana,
            Backup.estado == "FALLIDO"
        ).count()

        replicas_hoy = Replica.query.filter(
            Replica.fecha >= hoy, Replica.fecha < manana
        ).count()
        replicas_exitosas_hoy = Replica.query.filter(
            Replica.fecha >= hoy, Replica.fecha < manana,
            Replica.estado == "EXITOSO"
        ).count()
        replicas_fallidas_hoy = Replica.query.filter(
            Replica.fecha >= hoy, Replica.fecha < manana,
            Replica.estado == "FALLIDO"
        ).count()

        ultimo_backup = Backup.query.order_by(Backup.fecha.desc()).first()
        ultima_restauracion = Restauracion.query.order_by(Restauracion.fecha.desc()).first()

        espacio_total = db.session.query(db.func.sum(Backup.peso_bytes)).filter(
            Backup.estado == "EXITOSO"
        ).scalar() or 0

        errores_hoy = Log.query.filter(
            Log.fecha >= hoy, Log.fecha < manana,
            Log.nivel.in_(["ERROR", "CRITICAL"])
        ).count()

        return {
            "backups_hoy": backups_hoy,
            "backups_exitosos_hoy": backups_exitosos_hoy,
            "backups_fallidos_hoy": backups_fallidos_hoy,
            "replicas_hoy": replicas_hoy,
            "replicas_exitosas_hoy": replicas_exitosas_hoy,
            "replicas_fallidas_hoy": replicas_fallidas_hoy,
            "ultimo_backup": {
                "id": ultimo_backup.id, "archivo": ultimo_backup.archivo,
                "fecha": ultimo_backup.fecha.isoformat() if ultimo_backup else None,
                "estado": ultimo_backup.estado
            } if ultimo_backup else None,
            "ultima_restauracion": {
                "id": ultima_restauracion.id, "fecha": ultima_restauracion.fecha.isoformat(),
                "estado": ultima_restauracion.estado
            } if ultima_restauracion else None,
            "espacio_consumido_bytes": espacio_total,
            "errores_hoy": errores_hoy,
        }

    @staticmethod
    def obtener_ultimos_logs(limite: int = 50, nivel: str = None) -> list:
        q = Log.query.order_by(Log.fecha.desc())
        if nivel:
            q = q.filter(Log.nivel == nivel.upper())
        logs = q.limit(limite).all()
        return [
            {
                "id": l.id, "fecha": l.fecha.isoformat(), "nivel": l.nivel,
                "servicio": l.servicio, "mensaje": l.mensaje
            }
            for l in logs
        ]

    @staticmethod
    def _date_trunc(col):
        engine = db.engine.name
        if engine == "postgresql":
            return db.func.date_trunc("day", col)
        return db.func.date(col)

    @staticmethod
    def obtener_backups_por_dia(dias: int = 7) -> list:
        desde = datetime.utcnow() - timedelta(days=dias)
        trunc = MonitoringService._date_trunc(Backup.fecha)
        resultados = db.session.query(
            trunc.label("dia"),
            db.func.count(Backup.id).label("total"),
            db.func.sum(Backup.peso_bytes).label("peso")
        ).filter(Backup.fecha >= desde).group_by(
            trunc
        ).order_by("dia").all()

        return [
            {"fecha": r.dia.isoformat(), "total": r.total, "peso_bytes": r.peso or 0}
            for r in resultados
        ]

    @staticmethod
    def obtener_errores_por_dia(dias: int = 7) -> list:
        desde = datetime.utcnow() - timedelta(days=dias)
        trunc = MonitoringService._date_trunc(Log.fecha)
        resultados = db.session.query(
            trunc.label("dia"),
            db.func.count(Log.id).label("total")
        ).filter(
            Log.fecha >= desde,
            Log.nivel.in_(["ERROR", "CRITICAL"])
        ).group_by(
            trunc
        ).order_by("dia").all()

        return [{"fecha": r.dia.isoformat(), "total": r.total} for r in resultados]
