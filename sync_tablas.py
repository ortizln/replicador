#!/usr/bin/env python3
"""
sync_tablas.py
Replicación incremental por grupos con paralelismo interno (multiprocessing).

Mejoras:
- Script completo (el archivo previo estaba truncado)
- Manejo de errores por tabla sin tumbar todo el grupo
- Mensajes de Telegram robustos
- Upsert dinámico por PK (ON CONFLICT)
- Server-side cursor para leer en chunks
- Validaciones y cierre seguro de conexiones/lock
"""

import os
import time
import fcntl
import argparse
from datetime import datetime
from multiprocessing import Pool
from typing import Dict, List, Tuple, Any

import requests
import psycopg2
from psycopg2.extras import execute_values

# ==========================
# AJUSTES PRINCIPALES
# ==========================
DEFAULT_DIAS_REPLICACION = 1
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_PAGE_SIZE = 300
STATEMENT_TIMEOUT_MS = 0
LOCK_DIR = "/var/lock"

# ==========================
# TELEGRAM
# ==========================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def telegram_enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def enviar_telegram(mensaje: str) -> None:
    if not telegram_enabled():
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        requests.post(url, json=payload, timeout=20)
    except Exception:
        pass


# ==========================
# CONEXIONES
# ==========================
LOCAL_DB = {
    "host": os.getenv("LOCAL_DB_HOST", "192.168.0.88"),
    "port": int(os.getenv("LOCAL_DB_PORT", "5432")),
    "dbname": os.getenv("LOCAL_DB_NAME", "ErpEpmapaT"),
    "user": os.getenv("LOCAL_DB_USER", "postgres"),
    "password": os.getenv("LOCAL_DB_PASSWORD", ""),
}

REMOTE_DB = {
    "host": os.getenv("REMOTE_DB_HOST", "66.85.156.59"),
    "port": int(os.getenv("REMOTE_DB_PORT", "5432")),
    "dbname": os.getenv("REMOTE_DB_NAME", "ErpEpmapaT"),
    "user": os.getenv("REMOTE_DB_USER", "postgres"),
    "password": os.getenv("REMOTE_DB_PASSWORD", ""),
}

# ==========================
# GRUPOS
# ==========================
GRUPOS: Dict[str, List[Dict[str, str]]] = {
    "catalogos_mensual": [
        {"origen": "public.categorias", "destino": "public.categorias", "modo": "FULL"},
        {"origen": "public.modulos", "destino": "public.modulos", "modo": "FULL"},
        {"origen": "public.rubros", "destino": "public.rubros", "modo": "FULL"},
    ],
    "facturas_15min": [
        {"origen": "public.facturas", "destino": "public.facturas", "modo": "FACTURAS_VENTANA"},
        {"origen": "public.rubroxfac", "destino": "public.rubroxfac", "modo": "HIJA_FACTURAS", "fk_factura": "idfactura_facturas"},
    ],
    "fec_2veces_dia": [
        {"origen": "public.fec_factura", "destino": "public.fec_factura", "modo": "HIJA_FACTURAS"},
        {"origen": "public.fec_factura_detalles", "destino": "public.fec_factura_detalles", "modo": "HIJA_FACTURAS"},
        {"origen": "public.fec_factura_pagos", "destino": "public.fec_factura_pagos", "modo": "HIJA_FACTURAS"},
    ],
    "maestros_full": [
        {"origen": "public.abonados", "destino": "public.abonados", "modo": "FULL"},
        {"origen": "public.clientes", "destino": "public.clientes", "modo": "FULL"},
    ],
}


# ==========================
# LOCKFILE POR GRUPO
# ==========================
def lock_path_for_group(group: str) -> str:
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in group)
    return os.path.join(LOCK_DIR, f"replica_epmapat_{safe}.lock")


def adquirir_lock(lock_path: str):
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    lock_fd = open(lock_path, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd
    except BlockingIOError:
        lock_fd.close()
        return None


# ==========================
# HELPERS SQL
# ==========================
def set_timeouts(conn):
    if STATEMENT_TIMEOUT_MS and STATEMENT_TIMEOUT_MS > 0:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = %s", (STATEMENT_TIMEOUT_MS,))


def obtener_columnas(conn, tabla: str) -> List[str]:
    q = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = split_part(%s, '.', 1)
          AND table_name = split_part(%s, '.', 2)
        ORDER BY ordinal_position
    """
    with conn.cursor() as cur:
        cur.execute(q, (tabla, tabla))
        return [r[0] for r in cur.fetchall()]


def obtener_pk(conn, tabla: str) -> List[str]:
    q = """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = split_part(%s, '.', 1)
          AND tc.table_name = split_part(%s, '.', 2)
        ORDER BY kcu.ordinal_position
    """
    with conn.cursor() as cur:
        cur.execute(q, (tabla, tabla))
        return [r[0] for r in cur.fetchall()]


def build_select_sql(
    origen: str,
    modo: str,
    dias_ventana: int,
    fk_factura: str = "idfactura",
) -> Tuple[str, Tuple[Any, ...]]:
    """
    Construye SQL de extracción.

    Nota de precisión:
    - FACTURAS_VENTANA usa GREATEST(feccrea, COALESCE(fecmodi, feccrea)) para capturar
      filas nuevas y también editadas dentro de la ventana.
    - HIJA_FACTURAS filtra por la misma ventana sobre facturas y permite FK configurable.
    """
    if modo == "FULL":
        return f"SELECT * FROM {origen}", tuple()

    if modo == "FACTURAS_VENTANA":
        if dias_ventana <= 1:
            sql = f"""
                SELECT *
                FROM {origen}
                WHERE GREATEST(feccrea, COALESCE(fecmodi, feccrea)) >= date_trunc('day', now())
            """
            return sql, tuple()

        sql = f"""
            SELECT *
            FROM {origen}
            WHERE GREATEST(feccrea, COALESCE(fecmodi, feccrea)) >= (CURRENT_DATE - (%s * INTERVAL '1 day'))
        """
        return sql, (dias_ventana,)

    if modo == "HIJA_FACTURAS":
        if dias_ventana <= 1:
            sql = f"""
                SELECT h.*
                FROM {origen} h
                JOIN public.facturas f ON f.idfactura = h.{fk_factura}
                WHERE GREATEST(f.feccrea, COALESCE(f.fecmodi, f.feccrea)) >= date_trunc('day', now())
            """
            return sql, tuple()

        sql = f"""
            SELECT h.*
            FROM {origen} h
            JOIN public.facturas f ON f.idfactura = h.{fk_factura}
            WHERE GREATEST(f.feccrea, COALESCE(f.fecmodi, f.feccrea)) >= (CURRENT_DATE - (%s * INTERVAL '1 day'))
        """
        return sql, (dias_ventana,)

    raise ValueError(f"Modo no soportado: {modo}")


def construir_upsert(destino: str, columnas: List[str], pk_cols: List[str]) -> str:
    col_list = ", ".join(columnas)
    pk_list = ", ".join(pk_cols)

    cols_update = [c for c in columnas if c not in pk_cols]
    if not cols_update:
        return f"INSERT INTO {destino} ({col_list}) VALUES %s ON CONFLICT ({pk_list}) DO NOTHING"

    set_clause = ", ".join([f"{c}=EXCLUDED.{c}" for c in cols_update])
    return (
        f"INSERT INTO {destino} ({col_list}) VALUES %s "
        f"ON CONFLICT ({pk_list}) DO UPDATE SET {set_clause}"
    )


def replicar_tabla_streaming(
    local_conn,
    remote_conn,
    origen: str,
    destino: str,
    modo: str,
    dias_ventana: int,
    chunk_size: int,
    page_size: int,
    fk_factura: str = "idfactura",
) -> Dict[str, Any]:
    t0 = time.time()

    columnas = obtener_columnas(local_conn, origen)
    pk_cols = obtener_pk(remote_conn, destino)

    if not columnas:
        raise RuntimeError(f"No se encontraron columnas en {origen}")
    if not pk_cols:
        raise RuntimeError(f"No se encontró PK en {destino} (necesaria para upsert)")

    select_sql, params = build_select_sql(origen, modo, dias_ventana, fk_factura=fk_factura)
    upsert_sql = construir_upsert(destino, columnas, pk_cols)

    total = 0
    with local_conn.cursor(name=f"csr_{os.getpid()}_{int(time.time()*1000)}") as cur_src, remote_conn.cursor() as cur_dst:
        cur_src.itersize = chunk_size
        cur_src.execute(select_sql, params)

        while True:
            rows = cur_src.fetchmany(chunk_size)
            if not rows:
                break

            execute_values(cur_dst, upsert_sql, rows, page_size=page_size)
            remote_conn.commit()
            total += len(rows)

    return {
        "tabla": destino,
        "filas": total,
        "duracion_s": time.time() - t0,
        "ok": True,
    }


# Wrapper para multiprocessing
def replicar_wrapper(args):
    origen, destino, modo, dias_ventana, chunk_size, page_size, fk_factura = args
    local_conn = psycopg2.connect(**LOCAL_DB)
    remote_conn = psycopg2.connect(**REMOTE_DB)
    try:
        set_timeouts(local_conn)
        set_timeouts(remote_conn)
        return replicar_tabla_streaming(
            local_conn, remote_conn, origen, destino, modo,
            dias_ventana, chunk_size, page_size, fk_factura=fk_factura
        )
    except Exception as e:
        return {
            "tabla": destino,
            "filas": 0,
            "duracion_s": 0.0,
            "ok": False,
            "error": str(e),
        }
    finally:
        local_conn.close()
        remote_conn.close()


# ==========================
# CLI
# ==========================
def parse_args():
    p = argparse.ArgumentParser(description="Replicación por grupos EPMAPA-T (paralelo)")
    p.add_argument("--grupo", required=True, choices=sorted(GRUPOS.keys()), help="Grupo de tablas a replicar")
    p.add_argument("--dias", type=int, default=DEFAULT_DIAS_REPLICACION, help="Ventana de días")
    p.add_argument("--chunk", type=int, default=DEFAULT_CHUNK_SIZE, help="Filas por lote")
    p.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE, help="Page size de execute_values")
    p.add_argument("--proc", type=int, default=4, help="Número de procesos en paralelo")
    p.add_argument("--forzar-full", action="store_true", help="Replica TODO el grupo (ignora modos incrementales)")
    return p.parse_args()


# ==========================
# MAIN
# ==========================
def main():
    args = parse_args()
    grupo = args.grupo
    dias_ventana = args.dias
    chunk_size = args.chunk
    page_size = args.page_size
    procesos = max(1, args.proc)
    forzar_full = args.forzar_full

    tablas = GRUPOS.get(grupo, [])
    if not tablas:
        print(f"[{grupo}] No hay tablas configuradas.")
        enviar_telegram(f"⚠️ Grupo vacío: <b>{grupo}</b>")
        return 0

    lock_path = lock_path_for_group(grupo)
    lock_fd = adquirir_lock(lock_path)
    if not lock_fd:
        enviar_telegram(f"⏭️ Replicación omitida (<b>{grupo}</b>): lock activo.")
        print(f"[{grupo}] Otro proceso está ejecutándose. Saliendo.")
        return 0

    t0 = time.time()
    modo_txt = "FULL INICIAL" if forzar_full else "INCREMENTAL"
    enviar_telegram(f"🚀 Inicio replicación (<b>{grupo}</b>) [{modo_txt}] con {procesos} procesos")

    jobs = [
        (
            t["origen"],
            t["destino"],
            "FULL" if forzar_full else t.get("modo", "FULL"),
            dias_ventana,
            chunk_size,
            page_size,
            t.get("fk_factura", "idfactura"),
        )
        for t in tablas
    ]

    try:
        with Pool(processes=procesos) as pool:
            resultados = pool.map(replicar_wrapper, jobs)

        ok = [r for r in resultados if r.get("ok")]
        bad = [r for r in resultados if not r.get("ok")]
        total_filas = sum(r.get("filas", 0) for r in ok)
        dur_total = int(time.time() - t0)

        resumen = "\n".join(
            f"• {r['tabla']}: {r['filas']} filas ({r['duracion_s']:.1f}s)" for r in ok
        ) or "(sin tablas exitosas)"

        if bad:
            err_txt = "\n".join(f"• {r['tabla']}: {r.get('error', 'error')[:180]}" for r in bad)
            enviar_telegram(
                f"⚠️ Replicación con errores (<b>{grupo}</b>)\n"
                f"⏱️ {dur_total}s | 📦 {total_filas} filas\n\n"
                f"✅ OK:\n{resumen}\n\n"
                f"❌ Errores:\n{err_txt}"
            )
        else:
            enviar_telegram(
                f"✅ Replicación OK (<b>{grupo}</b>)\n"
                f"⏱️ {dur_total}s | 📦 {total_filas} filas\n\n{resumen}"
            )

        print(f"[{grupo}] fin en {dur_total}s | filas={total_filas} | ok={len(ok)} err={len(bad)}")
        return 0 if not bad else 2

    finally:
        try:
            lock_fd.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
