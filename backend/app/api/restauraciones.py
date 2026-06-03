from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.restauracion import Restauracion
from app.models.backup import Backup
from app.models.servidor import Servidor
from app.models.base_datos import BaseDatos
from app.services.restore_service import RestoreService
from app.models.auditoria import Auditoria
from app.utils.pagination import paginar_ordenar
from app.utils.async_ops import async_operation

bp = Blueprint("restauraciones", __name__, url_prefix="/api/restauraciones")


@bp.route("", methods=["GET"])
@jwt_required()
def listar():
    q = Restauracion.query
    pag, page, per_page = paginar_ordenar(q, Restauracion, default_sort="fecha", default_order="desc")
    return jsonify({
        "items": [{
            "id": r.id, "backup_id": r.backup_id, "servidor_id": r.servidor_id,
            "base_datos_id": r.base_datos_id, "usuario": r.usuario,
            "fecha": r.fecha.isoformat(), "estado": r.estado,
            "detalle": r.detalle, "duracion_segundos": r.duracion_segundos
        } for r in pag.items],
        "total": pag.total, "page": page, "per_page": per_page
    })


@bp.route("", methods=["POST"])
@jwt_required()
def restaurar():
    data = request.get_json()
    backup = Backup.query.get_or_404(data["backup_id"])
    servidor = Servidor.query.get_or_404(data["servidor_id"])
    base_datos = None
    if data.get("base_datos_id"):
        base_datos = BaseDatos.query.get(data["base_datos_id"])
    usuario = get_jwt_identity()

    def run():
        resultado = RestoreService.restaurar_backup(backup, servidor, base_datos_obj=base_datos, usuario=usuario)
        with db.session.begin():
            db.session.add(Auditoria(
                usuario=usuario, accion="Restauró respaldo",
                entidad="restauraciones",
                detalle=f"backup_id={backup.id}, servidor={servidor.nombre}"
            ))

    bd_nombre = base_datos.nombre_bd if base_datos else backup.base_datos.nombre_bd
    async_operation("RESTORE", f"Restauración: {bd_nombre}", run)
    return jsonify({"ok": True, "mensaje": f"Restauración de {bd_nombre} iniciada en segundo plano"}), 202
