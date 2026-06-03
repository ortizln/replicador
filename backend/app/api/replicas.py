import os
import tempfile
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.replica import Replica
from app.models.base_datos import BaseDatos
from app.models.servidor import Servidor
from app.services.replication_service import ReplicationService
from app.models.auditoria import Auditoria
from app.utils.pagination import paginar_ordenar
from app.utils.crypto import descifrar
from app.utils.async_ops import async_operation
from app.utils.notifications import notificar_replica

bp = Blueprint("replicas", __name__, url_prefix="/api/replicas")


@bp.route("", methods=["GET"])
@jwt_required()
def listar():
    q = Replica.query
    pag, page, per_page = paginar_ordenar(q, Replica, default_sort="fecha", default_order="desc")
    return jsonify({
        "items": [{
            "id": r.id, "origen_id": r.origen_id, "destino_id": r.destino_id,
            "tipo": r.tipo, "frecuencia": r.frecuencia,
            "fecha": r.fecha.isoformat(), "estado": r.estado,
            "filas_afectadas": r.filas_afectadas,
            "duracion_segundos": r.duracion_segundos,
            "detalle": r.detalle, "usuario": r.usuario
        } for r in pag.items],
        "total": pag.total, "page": page, "per_page": per_page
    })


@bp.route("", methods=["POST"])
@jwt_required()
def ejecutar():
    data = request.get_json()
    tipo = data.get("tipo", "COMPLETA")

    origen_bd = BaseDatos.query.get_or_404(data["origen_id"])
    destino_bd = BaseDatos.query.get_or_404(data["destino_id"])
    usuario = get_jwt_identity()

    desc = f"Réplica {origen_bd.nombre_bd} → {destino_bd.nombre_bd}"

    def run():
        if tipo == "COMPLETA":
            resultado = ReplicationService.replicar_completa(
                {
                    "host": origen_bd.host, "port": origen_bd.puerto,
                    "name": origen_bd.nombre_bd, "user": origen_bd.usuario_bd,
                    "password": descifrar(origen_bd.password_bd),
                },
                {
                    "host": destino_bd.host, "port": destino_bd.puerto,
                    "name": destino_bd.nombre_bd, "user": destino_bd.usuario_bd,
                    "password": descifrar(destino_bd.password_bd),
                    "ruta_backups": data.get("output_dir") or tempfile.gettempdir(),
                },
                usuario=usuario,
            )
        else:
            tablas = data.get("tablas", [])
            dias = data.get("dias_ventana", 1)
            resultado = ReplicationService.replicar_incremental(
                {
                    "host": origen_bd.host, "port": origen_bd.puerto,
                    "dbname": origen_bd.nombre_bd, "user": origen_bd.usuario_bd,
                    "password": descifrar(origen_bd.password_bd),
                },
                {
                    "host": destino_bd.host, "port": destino_bd.puerto,
                    "dbname": destino_bd.nombre_bd, "user": destino_bd.usuario_bd,
                    "password": descifrar(destino_bd.password_bd),
                },
                tablas, dias_ventana=dias,
            )

        with db.session.begin():
            replica = Replica(
                origen_id=data["origen_id"],
                destino_id=data["destino_id"],
                tipo=tipo,
                frecuencia=data.get("frecuencia", "MANUAL"),
                estado=estado,
                filas_afectadas=resultado.get("total_filas", 0),
                duracion_segundos=resultado.get("duracion_s"),
                detalle=str(resultado.get("error", "")),
                usuario=usuario,
            )
            db.session.add(replica)
            db.session.add(Auditoria(
                usuario=usuario, accion="Ejecutó replicación",
                entidad="replicas",
                detalle=f"origen={origen_bd.nombre_bd} destino={destino_bd.nombre_bd} tipo={tipo}"
            ))

        estado = "EXITOSO" if resultado["ok"] else "FALLIDO"
        notificar_replica(f"{origen_bd.nombre_bd} → {destino_bd.nombre_bd}", estado, resultado.get("error", ""))

    async_operation("REPLICA", desc, run)
    return jsonify({"ok": True, "mensaje": f"{desc} iniciada en segundo plano"}), 202
