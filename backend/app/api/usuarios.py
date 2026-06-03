from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from app import db
from app.models.usuario import Usuario
from app.utils.pagination import paginar_ordenar

bp = Blueprint("usuarios", __name__, url_prefix="/api/usuarios")


def _admin_required() -> bool:
    claims = get_jwt()
    return claims.get("rol") == "ADMINISTRADOR"


@bp.route("", methods=["GET"])
@jwt_required()
def listar():
    if not _admin_required():
        return jsonify({"error": "Solo administradores"}), 403
    q = Usuario.query
    pag, page, per_page = paginar_ordenar(q, Usuario, default_sort="username", default_order="asc")
    return jsonify({
        "items": [{
            "id": u.id, "username": u.username, "rol": u.rol,
            "activo": u.activo, "created_at": u.created_at.isoformat() if u.created_at else None,
        } for u in pag.items],
        "total": pag.total, "page": page, "per_page": per_page
    })


@bp.route("", methods=["POST"])
@jwt_required()
def crear():
    if not _admin_required():
        return jsonify({"error": "Solo administradores"}), 403
    data = request.get_json()
    if not data.get("username") or not data.get("password"):
        return jsonify({"error": "username y password requeridos"}), 400
    if Usuario.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "El usuario ya existe"}), 400
    import hashlib
    u = Usuario(
        username=data["username"],
        password=hashlib.sha256(data["password"].encode()).hexdigest(),
        rol=data.get("rol", "OPERADOR"),
        activo=data.get("activo", True),
    )
    db.session.add(u)
    db.session.commit()
    return jsonify({"ok": True, "id": u.id}), 201


@bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
def actualizar(id):
    if not _admin_required():
        return jsonify({"error": "Solo administradores"}), 403
    u = Usuario.query.get_or_404(id)
    data = request.get_json()
    import hashlib
    if "username" in data:
        u.username = data["username"]
    if "password" in data:
        u.password = hashlib.sha256(data["password"].encode()).hexdigest()
    if "rol" in data:
        u.rol = data["rol"]
    if "activo" in data:
        u.activo = data["activo"]
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def eliminar(id):
    if not _admin_required():
        return jsonify({"error": "Solo administradores"}), 403
    u = Usuario.query.get_or_404(id)
    db.session.delete(u)
    db.session.commit()
    return jsonify({"ok": True})
