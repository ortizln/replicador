from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models.log import Log
from app import db
from app.utils.pagination import paginar_ordenar

bp = Blueprint("logs", __name__, url_prefix="/api/logs")


@bp.route("", methods=["GET"])
@jwt_required()
def listar():
    q = Log.query

    nivel = request.args.get("nivel")
    if nivel:
        q = q.filter(Log.nivel == nivel.upper())

    servicio = request.args.get("servicio")
    if servicio:
        q = q.filter(Log.servicio == servicio.upper())

    fecha_desde = request.args.get("fecha_desde")
    if fecha_desde:
        q = q.filter(Log.fecha >= fecha_desde)

    fecha_hasta = request.args.get("fecha_hasta")
    if fecha_hasta:
        q = q.filter(Log.fecha <= fecha_hasta)

    mensaje = request.args.get("mensaje")
    if mensaje:
        q = q.filter(Log.mensaje.ilike(f"%{mensaje}%") | Log.detalle.ilike(f"%{mensaje}%"))

    pag, page, per_page = paginar_ordenar(q, Log, default_sort="fecha", default_order="desc")

    return jsonify({
        "items": [{
            "id": l.id, "fecha": l.fecha.isoformat(), "nivel": l.nivel,
            "servicio": l.servicio, "codigo": l.codigo,
            "mensaje": l.mensaje, "detalle": l.detalle,
            "usuario": l.usuario
        } for l in pag.items],
        "total": pag.total, "page": page, "per_page": per_page
    })


@bp.route("/niveles", methods=["GET"])
@jwt_required()
def niveles():
    return jsonify(["INFO", "WARN", "ERROR", "CRITICAL"])


@bp.route("/servicios", methods=["GET"])
@jwt_required()
def servicios():
    resultados = db.session.query(Log.servicio).distinct().all()
    return jsonify([r[0] for r in resultados if r[0]])
