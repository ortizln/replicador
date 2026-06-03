from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.services.monitoring_service import MonitoringService
from app.models.servidor import Servidor

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.route("/resumen", methods=["GET"])
@jwt_required()
def resumen():
    data = MonitoringService.obtener_estado_general()
    data["total_servidores"] = Servidor.query.count()
    data["servidores_activos"] = Servidor.query.filter_by(activo=True).count()
    return jsonify(data)


@bp.route("/backups-por-dia", methods=["GET"])
@jwt_required()
def backups_por_dia():
    from flask import request
    dias = request.args.get("dias", 7, type=int)
    return jsonify(MonitoringService.obtener_backups_por_dia(dias))


@bp.route("/errores-por-dia", methods=["GET"])
@jwt_required()
def errores_por_dia():
    from flask import request
    dias = request.args.get("dias", 7, type=int)
    return jsonify(MonitoringService.obtener_errores_por_dia(dias))
