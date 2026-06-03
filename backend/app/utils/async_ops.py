import threading
from app.utils.status import set_actual, clear_actual


def async_operation(tipo: str, descripcion: str, fn, *args, **kwargs):
    def _run():
        set_actual(tipo, descripcion)
        try:
            fn(*args, **kwargs)
        finally:
            clear_actual(tipo)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
