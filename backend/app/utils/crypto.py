import os
from cryptography.fernet import Fernet


def get_cipher():
    key = os.getenv("ENCRYPTION_KEY", "")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError):
        key = Fernet.generate_key()
        print(f"[WARN] ENCRYPTION_KEY inválida. Se generó una nueva: {key.decode()}")
        return Fernet(key)


def cifrar(texto: str) -> str:
    if not texto:
        return ""
    f = get_cipher()
    return f.encrypt(texto.encode()).decode()


def descifrar(token: str) -> str:
    if not token:
        return ""
    try:
        f = get_cipher()
        return f.decrypt(token.encode()).decode()
    except Exception:
        return "[ERROR: clave de cifrado ha cambiado]"
