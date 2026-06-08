import os
import subprocess
import time
from app.models.restauracion import Restauracion
from app.models.log import Log
from app.utils.crypto import descifrar
from app.utils.shell import quote as _quote, find_pg_restore as _find_pg_restore, find_pg_dump as _find_pg_dump
from app.utils.notifications import notificar_restauracion
from app import db


class RestoreService:

    @staticmethod
    def restaurar_backup(
        backup_obj, servidor_obj, base_datos_obj=None, usuario: str = "sistema"
    ) -> dict:
        t0 = time.time()
        archivo = backup_obj.archivo
        if not os.path.exists(archivo):
            return {"ok": False, "error": f"Archivo no encontrado: {archivo}"}

        bd = base_datos_obj if base_datos_obj else backup_obj.base_datos
        motor = bd.motor.lower()
        nombre_bd = bd.nombre_bd
        host = bd.host
        puerto = bd.puerto

        try:
            db_user = bd.usuario_bd
            db_pass = descifrar(bd.password_bd)

            if motor == "postgresql":
                env = os.environ.copy()
                env["PGPASSWORD"] = db_pass
                ext = os.path.splitext(archivo)[1].lower()
                pg_restore = _quote(_find_pg_restore())
                psql = _quote("psql")

                if ext in (".dump", ".backup"):
                    cmd = (
                        f"{pg_restore} -h {_quote(host)} -p {_quote(str(puerto))} "
                        f"-U {_quote(db_user)} -d {_quote(nombre_bd)} "
                        f"--clean --if-exists --no-owner --no-privileges "
                        f"{_quote(archivo)}"
                    )
                elif ext == ".sql":
                    cmd = f"{psql} -h {_quote(host)} -p {_quote(str(puerto))} -U {_quote(db_user)} -d {_quote(nombre_bd)} -f {_quote(archivo)}"
                elif archivo.endswith(".gz"):
                    gunzip = _quote("gunzip")
                    cmd = f"{gunzip} -c {_quote(archivo)} | {psql} -h {_quote(host)} -p {_quote(str(puerto))} -U {_quote(db_user)} -d {_quote(nombre_bd)}"
                elif ext == ".tar":
                    cmd = (
                        f"{pg_restore} -h {_quote(host)} -p {_quote(str(puerto))} "
                        f"-U {_quote(db_user)} -d {_quote(nombre_bd)} "
                        f"--clean --if-exists --no-owner --no-privileges "
                        f"-Ft {_quote(archivo)}"
                    )
                else:
                    cmd = (
                        f"{pg_restore} -h {_quote(host)} -p {_quote(str(puerto))} "
                        f"-U {_quote(db_user)} -d {_quote(nombre_bd)} "
                        f"--clean --if-exists --no-owner --no-privileges "
                        f"{_quote(archivo)}"
                    )
                result = subprocess.run(cmd, shell=True, check=False, env=env, capture_output=True, text=True)
                if result.returncode not in (0, 1):
                    raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)

            elif motor == "mysql":
                env = os.environ.copy()
                mysql = _quote("mysql")
                cmd = (
                    f"{mysql} -h {_quote(host)} -P {_quote(str(puerto))} "
                    f"-u {_quote(db_user)} "
                    f"-p{_quote(db_pass)} "
                    f"{_quote(nombre_bd)} < {_quote(archivo)}"
                )
                subprocess.run(cmd, shell=True, check=True, env=env, capture_output=True, text=True)
            else:
                return {"ok": False, "error": f"Motor no soportado: {motor}"}

            duracion = time.time() - t0
            rest = Restauracion(
                backup_id=backup_obj.id, servidor_id=servidor_obj.id,
                base_datos_id=bd.id,
                usuario=usuario, estado="EXITOSO", duracion_segundos=duracion,
            )
            db.session.add(rest)
            db.session.add(Log(
                nivel="INFO", servicio="RESTORE",
                mensaje=f"Restauración {nombre_bd} desde {backup_obj.archivo} OK",
                detalle=f"servidor={host}, duracion={duracion:.1f}s"
            ))
            db.session.commit()
            notificar_restauracion(nombre_bd, "EXITOSO", f"desde {backup_obj.archivo} en {host}")
            return {"ok": True, "restauracion_id": rest.id, "duracion_s": duracion}

        except subprocess.CalledProcessError as e:
            stderr = e.stderr if e.stderr else ""
            error_msg = str(e) + (f" | stderr: {stderr[:1000]}" if stderr else " (sin stderr)")
            duracion = time.time() - t0
            db.session.add(Restauracion(
                backup_id=backup_obj.id, servidor_id=servidor_obj.id,
                usuario=usuario, estado="FALLIDO", detalle=error_msg,
                duracion_segundos=duracion,
            ))
            db.session.add(Log(
                nivel="ERROR", servicio="RESTORE",
                mensaje=f"Restauración {nombre_bd} falló",
                detalle=error_msg
            ))
            db.session.commit()
            notificar_restauracion(nombre_bd, "FALLIDO", error_msg[:200])
            return {"ok": False, "error": error_msg, "duracion_s": duracion}
