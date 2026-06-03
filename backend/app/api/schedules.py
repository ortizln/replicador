from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from croniter import croniter
from app import db
from app.models.schedule import Schedule
from app.models.base_datos import BaseDatos
from app.models.auditoria import Auditoria
from app.services.backup_service import BackupService
from app.services.replication_service import ReplicationService
from app.utils.crypto import descifrar
from app.utils.async_ops import async_operation
from app.utils.pagination import paginar_ordenar

bp = Blueprint("schedules", __name__, url_prefix="/api/schedules")


def _proxima_ejecucion(s) -> str:
    try:
        cron = f"{s.cron_minuto} {s.cron_hora} {s.cron_dia} {s.cron_mes} {s.cron_semana}"
        base = s.ultima_ejecucion or datetime.now(timezone.utc)
        itr = croniter(cron, base)
        return itr.get_next(datetime).isoformat()
    except Exception:
        return None


@bp.route("", methods=["GET"])
@jwt_required()
def listar():
    q = Schedule.query
    pag, page, per_page = paginar_ordenar(q, Schedule, default_sort="id", default_order="asc")
    return jsonify({
        "items": [{
            "id": s.id, "nombre": s.nombre, "tipo": s.tipo,
            "id_bd": s.id_bd, "id_origen": s.id_origen, "id_destino": s.id_destino,
            "formato": s.formato, "compresion": s.compresion,
            "cron_minuto": s.cron_minuto, "cron_hora": s.cron_hora,
            "cron_dia": s.cron_dia, "cron_mes": s.cron_mes, "cron_semana": s.cron_semana,
            "activo": s.activo, "ultima_ejecucion": s.ultima_ejecucion.isoformat() if s.ultima_ejecucion else None,
            "proxima_ejecucion": _proxima_ejecucion(s),
            "ejecutando": s.ejecutando, "ultimo_resultado": s.ultimo_resultado
        } for s in pag.items],
        "total": pag.total, "page": page, "per_page": per_page
    })


def _int_or_none(v):
    if v is None or v == "" or v == 0:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


@bp.route("", methods=["POST"])
@jwt_required()
def crear():
    data = request.get_json()
    s = Schedule(
        nombre=data["nombre"], tipo=data["tipo"],
        id_bd=_int_or_none(data.get("id_bd")),
        id_origen=_int_or_none(data.get("id_origen")),
        id_destino=_int_or_none(data.get("id_destino")),
        formato=data.get("formato", "custom"),
        compresion=data.get("compresion") or None,
        cron_minuto=str(data.get("cron_minuto", "0")),
        cron_hora=str(data.get("cron_hora", "*")),
        cron_dia=str(data.get("cron_dia", "*")),
        cron_mes=str(data.get("cron_mes", "*")),
        cron_semana=str(data.get("cron_semana", "*")),
        activo=data.get("activo", True),
    )
    db.session.add(s)
    db.session.add(Auditoria(
        usuario=get_jwt_identity(), accion="Creó programación",
        entidad="horarios", detalle=f"nombre={s.nombre}, tipo={s.tipo}"
    ))
    db.session.commit()
    return jsonify({"id": s.id}), 201


@bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
def actualizar(id):
    s = Schedule.query.get_or_404(id)
    data = request.get_json()
    for campo in ("nombre", "tipo", "formato", "cron_minuto", "cron_hora",
                  "cron_dia", "cron_mes", "cron_semana", "activo"):
        if campo in data:
            setattr(s, campo, data[campo])
    if "id_bd" in data:
        s.id_bd = _int_or_none(data["id_bd"])
    if "id_origen" in data:
        s.id_origen = _int_or_none(data["id_origen"])
    if "id_destino" in data:
        s.id_destino = _int_or_none(data["id_destino"])
    if "compresion" in data:
        s.compresion = data["compresion"] or None
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def eliminar(id):
    s = Schedule.query.get_or_404(id)
    db.session.add(Auditoria(
        usuario=get_jwt_identity(), accion="Eliminó programación",
        entidad="horarios", detalle=f"nombre={s.nombre}"
    ))
    db.session.delete(s)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/<int:id>/ejecutar-ahora", methods=["POST"])
@jwt_required()
def ejecutar_ahora(id):
    s = Schedule.query.get_or_404(id)
    s.ejecutando = True
    s.ultimo_resultado = None
    db.session.commit()

    def run():
        from flask import current_app
        try:
            ok = True
            if s.tipo == "BACKUP":
                bd = BaseDatos.query.get(s.id_bd)
                if not bd:
                    ok = False
                else:
                    BackupService.generar_dump(bd, formato=s.formato or "custom")
            elif s.tipo == "REPLICA":
                origen = BaseDatos.query.get(s.id_origen)
                destino = BaseDatos.query.get(s.id_destino)
                if not origen or not destino:
                    ok = False
                else:
                    ReplicationService.replicar_completa(
                        {"host": origen.host, "port": origen.puerto, "name": origen.nombre_bd,
                         "user": origen.usuario_bd, "password": descifrar(origen.password_bd)},
                        {"host": destino.host, "port": destino.puerto, "name": destino.nombre_bd,
                         "user": destino.usuario_bd, "password": descifrar(destino.password_bd)},
                    )
            with current_app.app_context():
                s2 = db.session.get(Schedule, id)
                if s2:
                    s2.ejecutando = False
                    s2.ultima_ejecucion = datetime.now(timezone.utc)
                    s2.ultimo_resultado = "EXITOSO" if ok else "FALLIDO"
                    db.session.commit()
        except Exception as e:
            with current_app.app_context():
                s2 = db.session.get(Schedule, id)
                if s2:
                    s2.ejecutando = False
                    s2.ultimo_resultado = "FALLIDO"
                    db.session.commit()

    async_operation("SCHEDULE", f"Ejecutar ahora: {s.nombre}", run)
    return jsonify({"ok": True, "mensaje": f"{s.nombre} iniciada en segundo plano"}), 202
