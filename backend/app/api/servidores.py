import os
import socket
import paramiko
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.servidor import Servidor
from app.models.auditoria import Auditoria
from app.utils.pagination import paginar_ordenar
from datetime import datetime, timezone

bp = Blueprint("servidores", __name__, url_prefix="/api/servidores")


@bp.route("/test-connection", methods=["POST"])
@jwt_required()
def test_conexion():
    data = request.get_json()
    host = data.get("host", "")
    puerto = data.get("puerto", 22)
    usuario = data.get("usuario_ssh", "")
    clave = data.get("clave_ssh")

    if not host:
        return jsonify({"ok": False, "error": "Host es requerido"}), 400

    # 1. Test ping / reachability
    try:
        socket.setdefaulttimeout(5)
        socket.gethostbyname(host)
    except socket.gaierror:
        return jsonify({"ok": False, "error": f"No se pudo resolver el host: {host}", "paso": "dns"})

    # 2. Test TCP port
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, int(puerto)))
        sock.close()
        if result != 0:
            return jsonify({"ok": False, "error": f"Puerto {puerto} no accesible en {host}", "paso": "tcp"})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Error de conexión TCP: {str(e)}", "paso": "tcp"})

    # 3. Test SSH authentication
    if usuario:
        clave = data.get("clave_ssh", "")
        password = data.get("password", "")
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": host,
                "port": int(puerto),
                "username": usuario,
                "timeout": 10,
                "look_for_keys": True,
                "allow_agent": True,
            }

            if clave:
                if os.path.exists(clave) or '/' in clave or '\\' in clave:
                    connect_kwargs["key_filename"] = clave
                else:
                    connect_kwargs["password"] = clave
            if password:
                connect_kwargs["password"] = password

            ssh.connect(**connect_kwargs)

            stdin, stdout, stderr = ssh.exec_command("uname -a")
            uname = stdout.read().decode().strip()

            stdin, stdout, stderr = ssh.exec_command("df -h / | tail -1")
            disk = stdout.read().decode().strip()

            ssh.close()
            return jsonify({
                "ok": True,
                "mensaje": f"Conexión SSH exitosa a {host}:{puerto} como {usuario}",
                "paso": "ssh",
                "info": {
                    "sistema": uname,
                    "disco": disk,
                }
            })
        except paramiko.AuthenticationException:
            return jsonify({"ok": False, "error": "Autenticación SSH fallida. Verifica usuario, contraseña o clave SSH.", "paso": "auth"})
        except paramiko.SSHException as e:
            return jsonify({"ok": False, "error": f"Error SSH: {str(e)}", "paso": "ssh"})
        except Exception as e:
            return jsonify({"ok": False, "error": f"Error de conexión: {str(e)}", "paso": "ssh"})
    else:
        return jsonify({"ok": True, "mensaje": f"Host {host} accesible (puerto {puerto} abierto)", "paso": "tcp"})


@bp.route("", methods=["GET"])
@jwt_required()
def listar():
    q = Servidor.query
    pag, page, per_page = paginar_ordenar(q, Servidor, default_sort="id", default_order="asc")
    return jsonify({
        "items": [{
            "id": s.id, "nombre": s.nombre, "host": s.host,
            "puerto": s.puerto, "usuario_ssh": s.usuario_ssh,
            "ruta_backups": s.ruta_backups, "tipo": s.tipo, "activo": s.activo
        } for s in pag.items],
        "total": pag.total, "page": page, "per_page": per_page
    })


@bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def obtener(id):
    s = Servidor.query.get_or_404(id)
    return jsonify({
        "id": s.id, "nombre": s.nombre, "host": s.host,
        "puerto": s.puerto, "usuario_ssh": s.usuario_ssh,
        "ruta_backups": s.ruta_backups, "tipo": s.tipo, "activo": s.activo
    })


@bp.route("", methods=["POST"])
@jwt_required()
def crear():
    data = request.get_json()
    s = Servidor(
        nombre=data["nombre"], host=data["host"],
        puerto=data.get("puerto", 22),
        usuario_ssh=data.get("usuario_ssh"),
        clave_ssh=data.get("clave_ssh"),
        ruta_backups=data.get("ruta_backups"),
        tipo=data.get("tipo", "ORIGEN"),
        activo=data.get("activo", True),
    )
    db.session.add(s)
    db.session.add(Auditoria(
        usuario=get_jwt_identity(), accion="Creó servidor",
        entidad="servidores", detalle=f"nombre={s.nombre}, host={s.host}"
    ))
    db.session.commit()
    return jsonify({"id": s.id}), 201


@bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
def actualizar(id):
    s = Servidor.query.get_or_404(id)
    data = request.get_json()
    for campo in ("nombre", "host", "puerto", "usuario_ssh", "clave_ssh",
                  "ruta_backups", "tipo", "activo"):
        if campo in data:
            setattr(s, campo, data[campo])
    db.session.add(Auditoria(
        usuario=get_jwt_identity(), accion="Actualizó servidor",
        entidad="servidores", entidad_id=id,
        detalle=f"nombre={s.nombre}"
    ))
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def eliminar(id):
    s = Servidor.query.get_or_404(id)
    db.session.delete(s)
    db.session.add(Auditoria(
        usuario=get_jwt_identity(), accion="Eliminó servidor",
        entidad="servidores", entidad_id=id,
        detalle=f"nombre={s.nombre}"
    ))
    db.session.commit()
    return jsonify({"ok": True})
