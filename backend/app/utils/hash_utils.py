import hashlib
import os


def calcular_hash_sha256(filepath: str, chunk_size: int = 8192) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()


def verificar_integridad(filepath: str, hash_esperado: str) -> bool:
    if not os.path.exists(filepath):
        return False
    hash_real = calcular_hash_sha256(filepath)
    return hash_real == hash_esperado


def verificar_backup(filepath: str, hash_esperado: str, peso_esperado: int = None) -> dict:
    resultado = {
        "archivo": filepath,
        "existe": False,
        "hash_correcto": False,
        "peso_correcto": False,
        "hash_real": None,
        "peso_real": None,
    }

    if not os.path.exists(filepath):
        return resultado

    resultado["existe"] = True
    resultado["peso_real"] = os.path.getsize(filepath)
    resultado["hash_real"] = calcular_hash_sha256(filepath)

    if peso_esperado is not None:
        resultado["peso_correcto"] = resultado["peso_real"] == peso_esperado

    resultado["hash_correcto"] = resultado["hash_real"] == hash_esperado
    resultado["integro"] = resultado["hash_correcto"] and (resultado["peso_correcto"] if peso_esperado is not None else True)

    return resultado
