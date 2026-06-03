from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timezone
from app import db
from app.models.backup import Backup
from app.services.backup_service import BackupService
from app.services.transfer_service import TransferService
from app.models.auditoria import Auditoria
from app.models.log import Log
from app.utils.pagination import paginar_ordenar
from app.utils.async_ops import async_operation
from app.utils.notifications import notificar_transferencia
from app.utils.hash_utils import calcular_hash_sha256

bp = Blueprint("backups", __name__, url_prefix="/api/backups")


@bp.route("", methods=["GET"])
@jwt_required()
def listar():
    q = Backup.query
    id_bd = request.args.get("id_bd", type=int)
    if id_bd:
        q = q.filter_by(id_bd=id_bd)
    pag, page, per_page = paginar_ordenar(q, Backup, default_sort="fecha", default_order="desc")
    return jsonify({
        "items": [{
            "id": b.id, "id_bd": b.id_bd, "fecha": b.fecha.isoformat(),
            "tipo": b.tipo, "formato": b.formato,
            "archivo": b.archivo, "peso_bytes": b.peso_bytes,
            "hash_sha256": b.hash_sha256, "hash_verificado": b.hash_verificado,
            "estado": b.estado, "transferido": b.transferido, "usuario": b.usuario,
            "origen": {
                "nombre_bd": b.base_datos.nombre_bd,
                "motor": b.base_datos.motor,
                "host": b.base_datos.host,
                "puerto": b.base_datos.puerto,
                "servidor": b.base_datos.servidor.nombre if b.base_datos.servidor else None
            } if b.base_datos else None
        } for b in pag.items],
        "total": pag.total, "page": page, "per_page": per_page
    })


@bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def obtener(id):
    b = Backup.query.get_or_404(id)
    return jsonify({
        "id": b.id, "id_bd": b.id_bd, "fecha": b.fecha.isoformat(),
        "tipo": b.tipo, "formato": b.formato, "compresion": b.compresion,
        "archivo": b.archivo, "peso_bytes": b.peso_bytes,
        "hash_sha256": b.hash_sha256, "hash_verificado": b.hash_verificado,
        "estado": b.estado, "destino_externo": b.destino_externo,
        "transferido": b.transferido, "usuario": b.usuario,
        "origen": {
            "nombre_bd": b.base_datos.nombre_bd,
            "motor": b.base_datos.motor,
            "host": b.base_datos.host,
            "puerto": b.base_datos.puerto,
            "servidor": b.base_datos.servidor.nombre if b.base_datos.servidor else None
        } if b.base_datos else None
    })


@bp.route("", methods=["POST"])
@jwt_required()
def crear():
    from app.models.base_datos import BaseDatos
    data = request.get_json()
    bd = BaseDatos.query.get_or_404(data["id_bd"])
    usuario = get_jwt_identity()
    output_dir = data.get("output_dir")
    formato = data.get("formato", "custom")
    compresion = data.get("compresion")

    def run():
        resultado = BackupService.generar_dump(bd, output_dir, formato, compresion, usuario)
        if resultado.get("ok"):
            db.session.add(Auditoria(
                usuario=usuario, accion="Ejecutó backup",
                entidad="backups", entidad_id=resultado.get("backup_id"),
                detalle=f"bd={bd.nombre_bd}, archivo={resultado.get('archivo','')}"
            ))
            db.session.commit()

    async_operation("BACKUP", f"Backup: {bd.nombre_bd}", run)
    return jsonify({"ok": True, "mensaje": f"Backup de {bd.nombre_bd} iniciado en segundo plano"}), 202


@bp.route("/<int:id>/verificar", methods=["POST"])
@jwt_required()
def verificar(id):
    resultado = BackupService.verificar_backup_archivo(id)
    return jsonify(resultado)


@bp.route("/<int:id>/transferir", methods=["POST"])
@jwt_required()
def transferir(id):
    from app.models.servidor import Servidor
    data = request.get_json()
    backup = Backup.query.get_or_404(id)

    metodo = data.get("metodo", "scp")
    id_servidor = data.get("id_servidor")

    if metodo in ("scp", "sftp", "rsync"):
        if not id_servidor:
            return jsonify({"error": "id_servidor requerido"}), 400
        servidor = Servidor.query.get_or_404(id_servidor)
        svc = TransferService()
        fn = {
            "scp": svc.transferir_scp,
            "sftp": svc.transferir_sftp,
            "rsync": svc.transferir_rsync,
        }[metodo]
        resultado = fn(backup.archivo, {
            "host": servidor.host, "puerto": servidor.puerto,
            "usuario_ssh": servidor.usuario_ssh, "clave_ssh": servidor.clave_ssh,
            "ruta_backups": servidor.ruta_backups,
        })
    elif metodo == "s3":
        resultado = TransferService.transferir_s3(
            backup.archivo, data["bucket"],
            clave_s3=data.get("key"), endpoint_url=data.get("endpoint_url")
        )
    else:
        return jsonify({"error": f"Método no soportado: {metodo}"}), 400

    if resultado["ok"]:
        backup.transferido = True
        backup.destino_externo = f"{metodo}://{data.get('bucket', id_servidor)}"
        db.session.commit()

    nombre_destino = servidor.nombre if metodo in ("scp", "sftp", "rsync") and id_servidor else data.get('bucket', 'desconocido')
    if resultado["ok"]:
        notificar_transferencia(backup.archivo, nombre_destino, "EXITOSO")
    else:
        notificar_transferencia(backup.archivo, nombre_destino, "FALLIDO", resultado.get("error", ""))

    return jsonify(resultado)


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def eliminar(id):
    b = Backup.query.get_or_404(id)
    db.session.add(Auditoria(
        usuario=get_jwt_identity(), accion="Eliminó backup",
        entidad="backups", entidad_id=id,
        detalle=f"archivo={b.archivo}"
    ))
    db.session.delete(b)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/upload", methods=["POST"])
@jwt_required()
def subir_backup():
    from app.models.base_datos import BaseDatos
    from app.models.servidor import Servidor

    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400
    archivo = request.files["file"]
    if archivo.filename == "":
        return jsonify({"error": "Nombre de archivo vacío"}), 400

    id_bd = request.form.get("id_bd", type=int)
    if not id_bd:
        return jsonify({"error": "id_bd requerido"}), 400
    bd = BaseDatos.query.get(id_bd)
    if not bd:
        return jsonify({"error": "Base de datos no encontrada"}), 404

    backup_dir = os.getenv("BACKUP_DIR", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = secure_filename(archivo.filename) or f"upload_{ts}.dump"
    dest = os.path.join(backup_dir, f"{ts}_{safe_name}")
    archivo.save(dest)

    peso = os.path.getsize(dest)
    hash_val = calcular_hash_sha256(dest)
    usuario = get_jwt_identity()

    ext = os.path.splitext(safe_name)[1].lower()
    fmt = {"dump": "custom", "sql": "plain", "tar": "tar", "backup": "custom"}.get(ext.lstrip("."), "custom")

    backup = Backup(
        id_bd=id_bd, archivo=dest, peso_bytes=peso,
        hash_sha256=hash_val, hash_verificado=True,
        estado="EXITOSO", formato=fmt, usuario=usuario,
    )
    db.session.add(backup)
    db.session.add(Log(
        nivel="INFO", servicio="BACKUP",
        mensaje=f"Backup subido manualmente: {safe_name}",
        detalle=f"bd={bd.nombre_bd}, peso={peso}, hash={hash_val}"
    ))
    db.session.flush()

    transferir_a = request.form.get("transferir_a", type=int)
    metodo = request.form.get("metodo", "scp")
    if transferir_a:
        serv = Servidor.query.get(transferir_a)
        if serv:
            svc = TransferService()
            fn = {"scp": svc.transferir_scp, "sftp": svc.transferir_sftp, "rsync": svc.transferir_rsync}.get(metodo)
            if fn:
                try:
                    fn(dest, {"host": serv.host, "puerto": serv.puerto,
                              "usuario_ssh": serv.usuario_ssh, "clave_ssh": serv.clave_ssh,
                              "ruta_backups": serv.ruta_backups})
                    backup.transferido = True
                    backup.destino_externo = f"{metodo}://{serv.nombre}"
                except Exception as e:
                    db.session.add(Log(nivel="ERROR", servicio="TRANSFER",
                                       mensaje=f"Error al transferir {safe_name} a {serv.nombre}",
                                       detalle=str(e)[:500]))

    db.session.commit()
    return jsonify({"ok": True, "id": backup.id, "archivo": dest, "peso_bytes": peso, "hash_sha256": hash_val}), 201
