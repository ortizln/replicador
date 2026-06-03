from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.utils.status import get_actual

bp = Blueprint("status", __name__, url_prefix="/api/status")


@bp.route("/actual", methods=["GET"])
@jwt_required()
def actual():
    return jsonify(get_actual())
