from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.backup import Backup
from app.services.backup_service import BackupService
from app.services.transfer_service import TransferService
from app.models.auditoria import Auditoria
from app.utils.pagination import paginar_ordenar
from app.utils.async_ops import async_operation
from app.utils.notifications import notificar_transferencia

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
        with db.session.begin():
            resultado = BackupService.generar_dump(bd, output_dir, formato, compresion, usuario)
            if resultado.get("ok"):
                db.session.add(Auditoria(
                    usuario=usuario, accion="Ejecutó backup",
                    entidad="backups", entidad_id=resultado.get("backup_id"),
                    detalle=f"bd={bd.nombre_bd}, archivo={resultado.get('archivo','')}"
                ))

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
