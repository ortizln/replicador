import threading
from app.utils.status import set_actual, clear_actual

_app_instance = None

def _get_app():
    global _app_instance
    if _app_instance is None:
        from app import create_app
        _app_instance = create_app()
    return _app_instance


def async_operation(tipo: str, descripcion: str, fn, *args, **kwargs):
    def _run():
        app = _get_app()
        with app.app_context():
            set_actual(tipo, descripcion)
            try:
                fn(*args, **kwargs)
            finally:
                clear_actual(tipo)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
