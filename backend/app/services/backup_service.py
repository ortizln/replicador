import os
import subprocess
import time
import tempfile
import sys
from datetime import datetime
from pathlib import Path
from app.models.backup import Backup
from app.models.log import Log
from app.utils.hash_utils import calcular_hash_sha256, verificar_backup
from app.utils.notifications import notificar_backup
from app.utils.status import set_actual, clear_actual
from app.utils.shell import quote as _quote, find_pg_dump as _find_pg_dump
from app.services.transfer_service import TransferService
from app import db


class BackupService:

    @staticmethod
    def generar_dump(
        base_datos_obj,
        output_dir: str = None,
        formato: str = "custom",
        compresion: str = None,
        usuario: str = "sistema"
    ) -> dict:
        t0 = time.time()

        if not output_dir:
            output_dir = os.getenv("DUMP_DIR", tempfile.gettempdir())

        dump_dir = Path(output_dir)
        dump_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        nombre_bd = base_datos_obj.nombre_bd
        motor = base_datos_obj.motor.lower()

        ext_map = {"custom": ".dump", "plain": ".sql", "tar": ".tar", "directory": ""}
        ext = ext_map.get(formato, ".dump")
        archivo_base = dump_dir / f"{nombre_bd}_{ts}{ext}"

        try:
            set_actual("BACKUP", f"Backup: {nombre_bd}", 0)
            if motor == "postgresql":
                env = os.environ.copy()
                from app.utils.crypto import descifrar
                env["PGPASSWORD"] = descifrar(base_datos_obj.password_bd)

                pg_dump = _quote(_find_pg_dump())
                fmt_flag = {"custom": "-Fc", "plain": "-Fp", "tar": "-Ft", "directory": "-Fd"}.get(formato, "-Fc")
                cmd = (
                    f"{pg_dump} -h {_quote(str(base_datos_obj.host))} "
                    f"-p {_quote(str(base_datos_obj.puerto))} "
                    f"-U {_quote(base_datos_obj.usuario_bd)} "
                    f"-d {_quote(nombre_bd)} {fmt_flag} "
                    f"-f {_quote(str(archivo_base))}"
                )
                subprocess.run(cmd, shell=True, check=True, env=env, capture_output=True)

                if compresion == "gzip":
                    gzip_cmd = f"gzip -f {_quote(str(archivo_base))}"
                    subprocess.run(gzip_cmd, shell=True, check=True, env=env, capture_output=True)
                    archivo_final = Path(str(archivo_base) + ".gz")
                elif compresion == "zip":
                    zip_cmd = f"zip -j {_quote(str(archivo_base) + '.zip')} {_quote(str(archivo_base))}"
                    subprocess.run(zip_cmd, shell=True, check=True, env=env, capture_output=True)
                    archivo_final = Path(str(archivo_base) + ".zip")
                    if archivo_base.exists():
                        archivo_base.unlink()
                else:
                    archivo_final = archivo_base

            elif motor == "mysql":
                env = os.environ.copy()
                from app.utils.crypto import descifrar
                password = descifrar(base_datos_obj.password_bd)
                cmd = (
                    f"mysqldump -h {_quote(str(base_datos_obj.host))} "
                    f"-P {_quote(str(base_datos_obj.puerto))} "
                    f"-u {_quote(base_datos_obj.usuario_bd)} "
                    f"--password={_quote(password)} "
                    f"{_quote(nombre_bd)} > {_quote(str(archivo_base))}"
                )
                subprocess.run(cmd, shell=True, check=True, env=env, capture_output=True)
                archivo_final = archivo_base

            elif motor in ("mariadb",):
                env = os.environ.copy()
                from app.utils.crypto import descifrar
                password = descifrar(base_datos_obj.password_bd)
                cmd = (
                    f"mariadb-dump -h {_quote(str(base_datos_obj.host))} "
                    f"-P {_quote(str(base_datos_obj.puerto))} "
                    f"-u {_quote(base_datos_obj.usuario_bd)} "
                    f"--password={_quote(password)} "
                    f"{_quote(nombre_bd)} > {_quote(str(archivo_base))}"
                )
                subprocess.run(cmd, shell=True, check=True, env=env, capture_output=True)
                archivo_final = archivo_base

            else:
                return {"ok": False, "error": f"Motor no soportado: {motor}"}

            duracion = time.time() - t0
            peso = archivo_final.stat().st_size
            hash_file = calcular_hash_sha256(str(archivo_final))

            backup = Backup(
                id_bd=base_datos_obj.id,
                tipo="COMPLETO",
                formato=formato,
                compresion=compresion,
                archivo=str(archivo_final),
                peso_bytes=peso,
                hash_sha256=hash_file,
                hash_verificado=True,
                estado="EXITOSO",
                usuario=usuario,
            )
            db.session.add(backup)
            db.session.add(Log(
                nivel="INFO", servicio="BACKUP",
                mensaje=f"Backup {nombre_bd} OK",
                detalle=f"archivo={archivo_final}, hash={hash_file}, peso={peso}, duracion={duracion:.1f}s"
            ))
            db.session.commit()

            clear_actual("BACKUP")
            notificar_backup(
                nombre_bd=nombre_bd, archivo=str(archivo_final), estado="EXITOSO",
                hash_val=hash_file, peso=f"{peso} bytes", usuario=usuario,
            )

            _auto_transferir(backup)

            return {
                "ok": True, "backup_id": backup.id, "archivo": str(archivo_final),
                "hash_sha256": hash_file, "peso_bytes": peso, "duracion_s": duracion
            }

        except subprocess.CalledProcessError as e:
            stderr = ""
            if e.stderr:
                stderr = e.stderr.decode("utf-8", errors="replace")
            error_msg = str(e) + (f" | stderr: {stderr[:500]}" if stderr else " | stderr no capturado")
            db.session.add(Log(
                nivel="ERROR", servicio="BACKUP",
                mensaje=f"Backup {nombre_bd} falló",
                detalle=error_msg
            ))
            db.session.commit()
            clear_actual("BACKUP")
            notificar_backup(nombre_bd=nombre_bd, archivo="", estado="FALLIDO", usuario=usuario)
            return {"ok": False, "error": error_msg}

    @staticmethod
    def verificar_backup_archivo(backup_id: int) -> dict:
        backup = Backup.query.get(backup_id)
        if not backup:
            return {"ok": False, "error": "Backup no encontrado"}

        resultado = verificar_backup(backup.archivo, backup.hash_sha256, backup.peso_bytes)

        backup.hash_verificado = resultado["integro"]
        if not resultado["integro"]:
            backup.estado = "CORRUPTO"
            db.session.add(Log(
                nivel="WARN", servicio="BACKUP",
                codigo="INTEGRIDAD",
                mensaje=f"Backup {backup.id} NO pasó verificación de integridad",
                detalle=str(resultado)
            ))
        db.session.commit()

        return {"ok": True, "resultado": resultado}


def _auto_transferir(backup):
    import json
    from app.models.config import Config
    from app.models.servidor import Servidor
    from app.utils.notifications import notificar_transferencia

    raw = Config.query.filter_by(clave="AUTO_TRANSFER").first()
    if not raw or not raw.valor:
        return
    try:
        cfg = json.loads(raw.valor)
    except (json.JSONDecodeError, TypeError):
        return
    if not cfg.get("activo") or not cfg.get("servidores"):
        return

    metodo = cfg.get("metodo", "scp")
    svc = TransferService()
    fn = {"scp": svc.transferir_scp, "sftp": svc.transferir_sftp, "rsync": svc.transferir_rsync}.get(metodo)
    if not fn:
        return

    for sid in cfg["servidores"]:
        serv = Servidor.query.get(sid)
        if not serv:
            continue
        try:
            fn(backup.archivo, {
                "host": serv.host, "puerto": serv.puerto,
                "usuario_ssh": serv.usuario_ssh, "clave_ssh": serv.clave_ssh,
                "ruta_backups": serv.ruta_backups,
            })
            notificar_transferencia(backup.archivo, serv.nombre, "EXITOSO")
        except Exception as e:
            notificar_transferencia(backup.archivo, serv.nombre, "FALLIDO", str(e)[:200])
