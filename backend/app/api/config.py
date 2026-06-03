from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.config import Config
from app.utils.notifications import enviar_telegram
import json

bp = Blueprint("config", __name__, url_prefix="/api/config")


def _get_config(clave: str, default: str = "") -> str:
    conf = Config.query.filter_by(clave=clave).first()
    return conf.valor if conf else default


def _set_config(clave: str, valor: str):
    conf = Config.query.filter_by(clave=clave).first()
    if conf:
        conf.valor = valor
    else:
        conf = Config(clave=clave, valor=valor)
        db.session.add(conf)


@bp.route("/telegram", methods=["GET"])
@jwt_required()
def obtener_telegram():
    return jsonify({
        "TELEGRAM_BOT_TOKEN": _get_config("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHAT_ID": _get_config("TELEGRAM_CHAT_ID"),
    })


@bp.route("/telegram", methods=["PUT"])
@jwt_required()
def actualizar_telegram():
    data = request.get_json()
    for clave in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        _set_config(clave, data.get(clave, ""))
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/telegram/probar", methods=["POST"])
@jwt_required()
def probar_telegram():
    data = request.get_json()
    usuario = get_jwt_identity()

    for clave in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        _set_config(clave, data.get(clave, ""))
    db.session.commit()

    ok = enviar_telegram(
        f"🔔 <b>Prueba de Configuración</b>\n"
        f"👤 Usuario: {usuario}\n"
        f"📅 Si recibes esto, las notificaciones funcionan correctamente."
    )

    if ok:
        return jsonify({"ok": True, "mensaje": "✅ Mensaje de prueba enviado con éxito"})
    return jsonify({"ok": False, "mensaje": "❌ Error al enviar. Verifica Token y Chat ID"}), 400


@bp.route("/auto-transfer", methods=["GET"])
@jwt_required()
def obtener_auto_transfer():
    raw = _get_config("AUTO_TRANSFER", "{}")
    try:
        return jsonify(json.loads(raw))
    except (json.JSONDecodeError, TypeError):
        return jsonify({"activo": False, "servidores": [], "metodo": "scp"})


@bp.route("/auto-transfer", methods=["PUT"])
@jwt_required()
def actualizar_auto_transfer():
    data = request.get_json()
    _set_config("AUTO_TRANSFER", json.dumps({
        "activo": data.get("activo", False),
        "servidores": data.get("servidores", []),
        "metodo": data.get("metodo", "scp"),
    }))
    db.session.commit()
    return jsonify({"ok": True})
