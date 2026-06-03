import os
import requests
from flask import current_app


def _get_config(clave: str, default: str = "") -> str:
    try:
        from app.models.config import Config
        conf = Config.query.filter_by(clave=clave).first()
        if conf and conf.valor:
            return conf.valor
    except Exception:
        pass
    return os.getenv(clave, default)


def enviar_telegram(mensaje: str) -> bool:
    token = _get_config("TELEGRAM_BOT_TOKEN")
    chat_id = _get_config("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "HTML",
        }
        resp = requests.post(url, json=payload, timeout=15)
        return resp.status_code == 200
    except Exception:
        return False


def notificar_backup(nombre_bd: str, archivo: str, estado: str, hash_val: str = None, peso: str = None, usuario: str = None):
    icono = "✅" if estado == "EXITOSO" else "❌"
    texto = (
        f"{icono} <b>Backup {nombre_bd}</b>\n"
        f"📁 {archivo}\n"
        f"📊 Estado: {estado}\n"
    )
    if peso:
        texto += f"⚖️ Peso: {peso}\n"
    if hash_val:
        texto += f"🔐 SHA256: <code>{hash_val[:20]}...</code>\n"
    if usuario:
        texto += f"👤 Usuario: {usuario}"
    enviar_telegram(texto)


def notificar_replica(nombre: str, estado: str, detalle: str = ""):
    icono = "✅" if estado == "EXITOSO" else "❌"
    texto = f"{icono} <b>Replicación</b>\n{nombre}: {estado}"
    if detalle:
        texto += f"\n{detalle}"
    enviar_telegram(texto)


def notificar_restauracion(nombre_bd: str, estado: str, detalle: str = ""):
    icono = "✅" if estado == "EXITOSO" else "❌"
    texto = f"{icono} <b>Restauración {nombre_bd}</b>\n📊 Estado: {estado}"
    if detalle:
        texto += f"\n📝 {detalle}"
    enviar_telegram(texto)


def notificar_transferencia(archivo: str, servidor: str, estado: str, detalle: str = ""):
    icono = "✅" if estado == "EXITOSO" else "❌"
    texto = f"{icono} <b>Transferencia</b>\n📁 {archivo}\n🖥 {servidor}\n📊 Estado: {estado}"
    if detalle:
        texto += f"\n{detalle}"
    enviar_telegram(texto)
