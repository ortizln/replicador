import threading
from datetime import datetime, timezone

_tasks = {}
_lock = threading.Lock()


def set_actual(tipo: str, descripcion: str, id_ref: int = None):
    """Registra una operación en curso."""
    with _lock:
        _tasks[tipo] = {
            "tipo": tipo,
            "descripcion": descripcion,
            "id_ref": id_ref,
            "inicio": datetime.now(timezone.utc).isoformat(),
        }


def clear_actual(tipo: str):
    """Limpia una operación que finalizó."""
    with _lock:
        _tasks.pop(tipo, None)


def get_actual() -> list:
    """Retorna todas las operaciones en curso."""
    with _lock:
        return sorted(_tasks.values(), key=lambda t: t["inicio"], reverse=True)
