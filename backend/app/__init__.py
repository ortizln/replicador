import os
from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()


def make_celery(app=None):
    celery = Celery(
        app.import_name if app else __name__,
        backend=app.config.get("CELERY_RESULT_BACKEND") if app else os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        broker=app.config.get("CELERY_BROKER_URL") if app else os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    )
    if app:
        celery.conf.update(app.config)
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        celery.Task = ContextTask
    return celery


celery_app = make_celery()
celery_app.conf.beat_schedule = {
    "disparar-programaciones": {
        "task": "app.tasks.celery_tasks.disparar_programaciones",
        "schedule": 60.0,
    },
}
celery_app.conf.imports = ["app.tasks.celery_tasks"]


def _seed_default_users():
    from app.models.usuario import Usuario
    import hashlib
    if Usuario.query.count() == 0:
        db.session.add_all([
            Usuario(username="admin", password=hashlib.sha256(b"admin123").hexdigest(), rol="ADMINISTRADOR"),
            Usuario(username="operador", password=hashlib.sha256(b"operador123").hexdigest(), rol="OPERADOR"),
            Usuario(username="auditor", password=hashlib.sha256(b"auditor123").hexdigest(), rol="AUDITOR"),
        ])
        db.session.commit()


def _migrar_schema():
    import sqlalchemy as sa
    insp = sa.inspect(db.engine)
    cols = [c["name"] for c in insp.get_columns("horarios")]
    if "ejecutando" not in cols:
        db.session.execute(sa.text("ALTER TABLE horarios ADD COLUMN ejecutando BOOLEAN DEFAULT FALSE"))
    if "ultimo_resultado" not in cols:
        db.session.execute(sa.text("ALTER TABLE horarios ADD COLUMN ultimo_resultado VARCHAR(50)"))
    db.session.commit()


def create_app(config_name="default"):
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-secret")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///replicador.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["CELERY_BROKER_URL"] = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    app.config["CELERY_RESULT_BACKEND"] = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    app.config["ENCRYPTION_KEY"] = os.getenv("ENCRYPTION_KEY", "")

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    from app.models import servidor, base_datos, backup, replica, restauracion, log, auditoria, config, schedule, usuario

    from app.api import auth, servidores, bases_datos, backups, replicas, restauraciones, logs, dashboard, config, status, schedules, usuarios

    app.register_blueprint(auth.bp)
    app.register_blueprint(servidores.bp)
    app.register_blueprint(bases_datos.bp)
    app.register_blueprint(backups.bp)
    app.register_blueprint(replicas.bp)
    app.register_blueprint(restauraciones.bp)
    app.register_blueprint(logs.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(config.bp)
    app.register_blueprint(status.bp)
    app.register_blueprint(schedules.bp)
    app.register_blueprint(usuarios.bp)

    with app.app_context():
        db.create_all()
        _migrar_schema()
        _seed_default_users()

    return app
