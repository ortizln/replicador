from app import celery_app, create_app
from app.services.backup_service import BackupService
from app.services.replication_service import ReplicationService
from app.models.base_datos import BaseDatos
from app.models.servidor import Servidor
from app.models.log import Log
from app.utils.crypto import descifrar
from app import db

app = create_app()


@celery_app.task(bind=True, max_retries=3)
def ejecutar_backup_programado(self, id_bd: int, output_dir: str = None, formato: str = "custom"):
    with app.app_context():
        bd = BaseDatos.query.get(id_bd)
        if not bd:
            return {"ok": False, "error": "Base de datos no encontrada"}
        resultado = BackupService.generar_dump(bd, output_dir, formato)
        return resultado


@celery_app.task(bind=True, max_retries=3)
def ejecutar_replica_programada(self, origen_id: int, destino_id: int, tipo: str = "COMPLETA"):
    with app.app_context():
        origen = BaseDatos.query.get(origen_id)
        destino = BaseDatos.query.get(destino_id)
        if not origen or not destino:
            return {"ok": False, "error": "Base de datos origen/destino no encontrada"}

        if tipo == "COMPLETA":
            resultado = ReplicationService.replicar_completa(
                {
                    "host": origen.host, "port": origen.puerto,
                    "name": origen.nombre_bd, "user": origen.usuario_bd,
                    "password": descifrar(origen.password_bd),
                },
                {
                    "host": destino.host, "port": destino.puerto,
                    "name": destino.nombre_bd, "user": destino.usuario_bd,
                    "password": descifrar(destino.password_bd),
                },
            )
        else:
            resultado = {"ok": False, "error": "Incremental no soportado en tarea programada aún"}
        return resultado


@celery_app.task
def verificar_backups_pendientes():
    with app.app_context():
        from app.models.backup import Backup
        from app.utils.hash_utils import verificar_backup

        backups = Backup.query.filter(
            Backup.estado == "EXITOSO",
            Backup.hash_verificado == False
        ).limit(50).all()

        verificados = 0
        for b in backups:
            res = verificar_backup(b.archivo, b.hash_sha256, b.peso_bytes)
            b.hash_verificado = res["integro"]
            if not res["integro"]:
                b.estado = "CORRUPTO"
                db.session.add(Log(
                    nivel="WARN", servicio="BACKUP",
                    codigo="INTEGRIDAD",
                    mensaje=f"Verificación automática: Backup {b.id} corrupto"
                ))
            verificados += 1

        db.session.commit()
        return {"verificados": verificados}


@celery_app.task
def limpiar_logs_viejos(dias: int = 30):
    with app.app_context():
        from datetime import datetime, timedelta
        from app.models.log import Log

        corte = datetime.utcnow() - timedelta(days=dias)
        eliminados = Log.query.filter(Log.fecha < corte).delete()
        db.session.commit()
        return {"eliminados": eliminados}


@celery_app.task
def disparar_programaciones():
    with app.app_context():
        from app.models.schedule import Schedule
        from app.models.base_datos import BaseDatos
        from app.models.log import Log
        from app.services.backup_service import BackupService
        from app.services.replication_service import ReplicationService
        from app.utils.crypto import descifrar
        from datetime import datetime, timezone
        from croniter import croniter

        schedules = Schedule.query.filter_by(activo=True).all()
        now = datetime.now(timezone.utc)
        ejecutadas = 0

        for s in schedules:
            cron = f"{s.cron_minuto} {s.cron_hora} {s.cron_dia} {s.cron_mes} {s.cron_semana}"
            base = s.ultima_ejecucion or datetime.now(timezone.utc)

            try:
                itr = croniter(cron, base)
                next_run = itr.get_next(datetime)
            except Exception:
                continue

            if now >= next_run:
                try:
                    if s.tipo == "BACKUP":
                        bd = BaseDatos.query.get(s.id_bd)
                        if bd:
                            BackupService.generar_dump(bd, formato=s.formato or "custom")
                    elif s.tipo == "REPLICA":
                        origen = BaseDatos.query.get(s.id_origen)
                        destino = BaseDatos.query.get(s.id_destino)
                        if origen and destino:
                            ReplicationService.replicar_completa(
                                {"host": origen.host, "port": origen.puerto, "name": origen.nombre_bd,
                                 "user": origen.usuario_bd, "password": descifrar(origen.password_bd)},
                                {"host": destino.host, "port": destino.puerto, "name": destino.nombre_bd,
                                 "user": destino.usuario_bd, "password": descifrar(destino.password_bd)},
                            )
                except Exception as e:
                    db.session.add(Log(
                        nivel="ERROR", servicio="SCHEDULE",
                        mensaje=f"Programación {s.nombre} falló",
                        detalle=str(e)[:500]
                    ))
                    db.session.commit()
                else:
                    s.ultima_ejecucion = now
                    db.session.commit()
                ejecutadas += 1

        return {"ejecutadas": ejecutadas, "revisadas": len(schedules)}
