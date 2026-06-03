import os
import subprocess
import paramiko
from app.models.log import Log
from app.utils.shell import quote
from app import db


def _connect_kwargs(sd: dict) -> dict:
    kws = {
        "hostname": sd["host"],
        "port": sd["puerto"],
        "username": sd.get("usuario_ssh"),
        "timeout": 15,
    }
    clave = sd.get("clave_ssh", "")
    password = sd.get("password", "")
    if clave:
        if os.path.exists(clave) or "/" in clave or "\\" in clave:
            kws["key_filename"] = clave
        else:
            kws["password"] = clave
    if password:
        kws["password"] = password
    return kws


class TransferService:

    @staticmethod
    def transferir_scp(archivo_local: str, servidor_destino: dict, ruta_remota: str = None) -> dict:
        destino = ruta_remota or servidor_destino.get("ruta_backups", "/tmp")
        try:
            cmd = (
                f"scp -P {servidor_destino['puerto']} "
                f"{quote(archivo_local)} "
                f"{quote(servidor_destino['usuario_ssh'])}@{quote(servidor_destino['host'])}:{quote(destino)}"
            )
            subprocess.run(cmd, shell=True, check=True)
            db.session.add(Log(
                nivel="INFO", servicio="TRANSFER",
                mensaje=f"SCP OK {archivo_local} -> {servidor_destino['host']}:{destino}"
            ))
            db.session.commit()
            return {"ok": True}
        except subprocess.CalledProcessError as e:
            stderr = e.stderr[:500] if e.stderr else str(e)
            _escanear_error(stderr, "SCP", archivo_local, servidor_destino['host'])
            db.session.add(Log(
                nivel="ERROR", servicio="TRANSFER",
                mensaje=f"SCP falló {archivo_local} -> {servidor_destino['host']}",
                detalle=stderr
            ))
            db.session.commit()
            return {"ok": False, "error": stderr}

    @staticmethod
    def transferir_sftp(archivo_local: str, servidor_destino: dict, ruta_remota: str = None) -> dict:
        destino = ruta_remota or servidor_destino.get("ruta_backups", "/tmp")
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(**_connect_kwargs(servidor_destino))
            sftp = ssh.open_sftp()
            sftp.put(archivo_local, os.path.join(destino, os.path.basename(archivo_local)))
            sftp.close()
            ssh.close()

            db.session.add(Log(
                nivel="INFO", servicio="TRANSFER",
                mensaje=f"SFTP OK {archivo_local} -> {servidor_destino['host']}:{destino}"
            ))
            db.session.commit()
            return {"ok": True}
        except Exception as e:
            _escanear_error(str(e), "SFTP", archivo_local, servidor_destino.get("host", "?"))
            db.session.add(Log(
                nivel="ERROR", servicio="TRANSFER",
                mensaje=f"SFTP falló {archivo_local} -> {servidor_destino.get('host','?')}",
                detalle=str(e)
            ))
            db.session.commit()
            return {"ok": False, "error": str(e)}

    @staticmethod
    def transferir_rsync(archivo_local: str, servidor_destino: dict, ruta_remota: str = None) -> dict:
        destino = ruta_remota or servidor_destino.get("ruta_backups", "/tmp")
        try:
            cmd = (
                f"rsync -avz -e 'ssh -p {servidor_destino['puerto']}' "
                f"{quote(archivo_local)} "
                f"{quote(servidor_destino['usuario_ssh'])}@{quote(servidor_destino['host'])}:{quote(destino)}"
            )
            subprocess.run(cmd, shell=True, check=True)

            db.session.add(Log(
                nivel="INFO", servicio="TRANSFER",
                mensaje=f"Rsync OK {archivo_local} -> {servidor_destino['host']}:{destino}"
            ))
            db.session.commit()
            return {"ok": True}
        except subprocess.CalledProcessError as e:
            stderr = e.stderr[:500] if e.stderr else str(e)
            _escanear_error(stderr, "RSYNC", archivo_local, servidor_destino['host'])
            db.session.add(Log(
                nivel="ERROR", servicio="TRANSFER",
                mensaje=f"Rsync falló {archivo_local} -> {servidor_destino['host']}",
                detalle=stderr
            ))
            db.session.commit()
            return {"ok": False, "error": stderr}

    @staticmethod
    def transferir_s3(archivo_local: str, bucket: str, clave_s3: str = None, endpoint_url: str = None) -> dict:
        try:
            import boto3
            session = boto3.Session()
            client_kwargs = {}
            if endpoint_url:
                client_kwargs["endpoint_url"] = endpoint_url
            s3 = session.client("s3", **client_kwargs)
            key = clave_s3 or os.path.basename(archivo_local)
            s3.upload_file(archivo_local, bucket, key)

            db.session.add(Log(
                nivel="INFO", servicio="TRANSFER",
                mensaje=f"S3 OK {archivo_local} -> s3://{bucket}/{key}"
            ))
            db.session.commit()
            return {"ok": True, "key": key}
        except Exception as e:
            db.session.add(Log(
                nivel="ERROR", servicio="TRANSFER",
                mensaje=f"S3 falló {archivo_local} -> {bucket}",
                detalle=str(e)
            ))
            db.session.commit()
            return {"ok": False, "error": str(e)}

    @staticmethod
    def transferir_ftp(archivo_local: str, host: str, usuario: str, password: str, ruta: str = "/") -> dict:
        try:
            import ftplib
            ftp = ftplib.FTP(host)
            ftp.login(usuario, password)
            with open(archivo_local, "rb") as f:
                ftp.storbinary(f"STOR {os.path.basename(archivo_local)}", f)
            ftp.quit()

            db.session.add(Log(
                nivel="INFO", servicio="TRANSFER",
                mensaje=f"FTP OK {archivo_local} -> {host}"
            ))
            db.session.commit()
            return {"ok": True}
        except Exception as e:
            _escanear_error(str(e), "FTP", archivo_local, host)
            db.session.add(Log(
                nivel="ERROR", servicio="TRANSFER",
                mensaje=f"FTP falló {archivo_local} -> {host}",
                detalle=str(e)
            ))
            db.session.commit()
            return {"ok": False, "error": str(e)}


def _escanear_error(stderr: str, servicio: str, archivo: str, host: str):
    import re
    errores_permiso = [
        (r"Permission denied", "Permiso denegado — revisa credenciales SSH"),
        (r"not a regular file", "No es un archivo regular — revisa la ruta"),
        (r"No such file", "Ruta no encontrada en el servidor destino"),
        (r"Connection refused", "Conexión rechazada — ¿el servidor SSH está corriendo?"),
        (r"Connection timed out", "Timeout de conexión — revisa firewall/host"),
        (r"Could not resolve hostname", "Hostname no resuelve — revisa el nombre del servidor"),
        (r"lost connection", "Conexión perdida durante la transferencia"),
        (r"Authentication failed", "Autenticación SSH fallida"),
        (r"Permission denied \(publickey", "Autenticación con llave pública fallida"),
        (r"mkdir.*Permission denied", "No hay permisos de escritura en el directorio destino"),
        (r"cannot remove", "No hay permisos para sobrescribir archivo en destino"),
        (r"Broken pipe", "Conexión interrumpida durante la transferencia"),
    ]
    for patron, mensaje in errores_permiso:
        if re.search(patron, stderr, re.IGNORECASE):
            db.session.add(Log(
                nivel="WARN", servicio=servicio, codigo="PERMISO",
                mensaje=f"{mensaje}: {host}",
                detalle=f"archivo={archivo}, host={host}"
            ))
            db.session.commit()
            return
