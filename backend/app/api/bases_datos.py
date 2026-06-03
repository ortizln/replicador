import socket
import psycopg2
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.base_datos import BaseDatos
from app.utils.crypto import cifrar, descifrar
from app.utils.pagination import paginar_ordenar

bp = Blueprint("bases_datos", __name__, url_prefix="/api/bases-datos")


@bp.route("/test-connection", methods=["POST"])
@jwt_required()
def test_conexion():
    data = request.get_json()
    motor = data.get("motor", "postgresql").lower()
    host = data.get("host", "")
    puerto = data.get("puerto", 5432)
    nombre_bd = data.get("nombre_bd", "")
    usuario = data.get("usuario_bd", "")
    password = data.get("password_bd", "")

    if not host or not nombre_bd:
        return jsonify({"ok": False, "error": "Host y nombre BD son requeridos"}), 400

    # 1. Test resolución DNS
    try:
        socket.setdefaulttimeout(5)
        socket.gethostbyname(host)
    except socket.gaierror:
        return jsonify({"ok": False, "error": f"No se pudo resolver el host: {host}", "paso": "dns"})

    # 2. Test TCP
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, int(puerto)))
        sock.close()
        if result != 0:
            return jsonify({"ok": False, "error": f"Puerto {puerto} no accesible en {host}", "paso": "tcp"})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Error TCP: {str(e)}", "paso": "tcp"})

    # 3. Test autenticación BD
    try:
        if motor == "postgresql":
            conn = psycopg2.connect(
                host=host, port=int(puerto), dbname=nombre_bd,
                user=usuario, password=password, connect_timeout=5
            )
            cur = conn.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            cur.execute("SELECT current_database(), pg_size_pretty(pg_database_size(current_database()))")
            db_info = cur.fetchone()
            conn.close()
            return jsonify({
                "ok": True,
                "mensaje": f"Conexión exitosa a {nombre_bd}",
                "paso": "bd",
                "info": {"version": version, "basedatos": db_info[0], "tamano": db_info[1]}
            })
        elif motor in ("mysql", "mariadb"):
            import pymysql
            conn = pymysql.connect(
                host=host, port=int(puerto), database=nombre_bd,
                user=usuario, password=password, connect_timeout=5
            )
            cur = conn.cursor()
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()[0]
            conn.close()
            return jsonify({
                "ok": True,
                "mensaje": f"Conexión exitosa a {nombre_bd}",
                "paso": "bd",
                "info": {"version": version}
            })
        else:
            return jsonify({"ok": False, "error": f"Motor no soportado: {motor}", "paso": "motor"})

    except psycopg2.OperationalError as e:
        return jsonify({"ok": False, "error": f"Error de conexión BD: {str(e).strip()}", "paso": "bd"})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Error: {str(e)}", "paso": "bd"})


@bp.route("", methods=["GET"])
@jwt_required()
def listar():
    q = BaseDatos.query
    id_servidor = request.args.get("id_servidor", type=int)
    if id_servidor:
        q = q.filter_by(id_servidor=id_servidor)
    pag, page, per_page = paginar_ordenar(q, BaseDatos, default_sort="id", default_order="asc")
    return jsonify({
        "items": [{
            "id": b.id, "id_servidor": b.id_servidor, "motor": b.motor,
            "nombre_bd": b.nombre_bd, "host": b.host, "puerto": b.puerto,
            "usuario_bd": b.usuario_bd
        } for b in pag.items],
        "total": pag.total, "page": page, "per_page": per_page
    })


@bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def obtener(id):
    b = BaseDatos.query.get_or_404(id)
    return jsonify({
        "id": b.id, "id_servidor": b.id_servidor, "motor": b.motor,
        "nombre_bd": b.nombre_bd, "host": b.host, "puerto": b.puerto,
        "usuario_bd": b.usuario_bd
    })


@bp.route("", methods=["POST"])
@jwt_required()
def crear():
    data = request.get_json()
    b = BaseDatos(
        id_servidor=data["id_servidor"],
        motor=data["motor"],
        nombre_bd=data["nombre_bd"],
        host=data.get("host"),
        puerto=data.get("puerto"),
        usuario_bd=data.get("usuario_bd"),
        password_bd=cifrar(data.get("password_bd", "")),
    )
    db.session.add(b)
    db.session.commit()
    return jsonify({"id": b.id}), 201


@bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
def actualizar(id):
    b = BaseDatos.query.get_or_404(id)
    data = request.get_json()
    for campo in ("motor", "nombre_bd", "host", "puerto", "usuario_bd"):
        if campo in data:
            setattr(b, campo, data[campo])
    if "password_bd" in data:
        b.password_bd = cifrar(data["password_bd"])
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def eliminar(id):
    b = BaseDatos.query.get_or_404(id)
    db.session.delete(b)
    db.session.commit()
    return jsonify({"ok": True})
