from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import hashlib

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

USERS = {
    "admin": {"password": "admin123", "rol": "ADMINISTRADOR"},
    "operador": {"password": "operador123", "rol": "OPERADOR"},
    "auditor": {"password": "auditor123", "rol": "AUDITOR"},
}


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")

    user = USERS.get(username)
    if user and user["password"] == password:
        token = create_access_token(
            identity=username,
            additional_claims={"rol": user["rol"]}
        )
        return jsonify({"access_token": token, "rol": user["rol"]})

    from app.models.usuario import Usuario
    u = Usuario.query.filter_by(username=username, activo=True).first()
    if u and u.password == hashlib.sha256(password.encode()).hexdigest():
        token = create_access_token(
            identity=u.username,
            additional_claims={"rol": u.rol}
        )
        return jsonify({"access_token": token, "rol": u.rol})

    return jsonify({"error": "Credenciales inválidas"}), 401


@bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    return jsonify({"usuario": get_jwt_identity()})
