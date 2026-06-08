import os
import subprocess
import tempfile
import time
from datetime import datetime
from app.models.backup import Backup
from app.models.replica import Replica
from app.models.log import Log
from app.utils.hash_utils import calcular_hash_sha256
from app.utils.shell import quote as _quote, find_pg_dump as _find_pg_dump, find_pg_restore as _find_pg_restore
from app import db


class ReplicationService:

    @staticmethod
    def replicar_completa(origen: dict, destino: dict, usuario: str = "sistema") -> dict:
        ts = datetime.utcnow()
        dump_dir = destino.get("ruta_backups", tempfile.gettempdir())
        os.makedirs(dump_dir, exist_ok=True)

        nombre_dump = f"{origen['name']}_full_{ts.strftime('%Y%m%d_%H%M%S')}.dump"
        dump_file = os.path.join(dump_dir, nombre_dump)

        t0 = time.time()
        try:
            env_src = os.environ.copy()
            env_src["PGPASSWORD"] = origen["password"]
            env_dst = os.environ.copy()
            env_dst["PGPASSWORD"] = destino["password"]

            pg_dump = _quote(_find_pg_dump())
            dump_cmd = (
                f"{pg_dump} -h {_quote(origen['host'])} -p {_quote(str(origen['port']))} "
                f"-U {_quote(origen['user'])} -d {_quote(origen['name'])} "
                f"-Fc -f {_quote(dump_file)}"
            )
            result = subprocess.run(dump_cmd, shell=True, check=True, env=env_src, capture_output=True, text=True)

            hash_file = calcular_hash_sha256(dump_file)
            peso = os.path.getsize(dump_file)

            pg_restore = _quote(_find_pg_restore())
            restore_cmd = (
                f"{pg_restore} -h {_quote(destino['host'])} -p {_quote(str(destino['port']))} "
                f"-U {_quote(destino['user'])} -d {_quote(destino['name'])} "
                f"--clean --if-exists --no-owner --no-privileges --jobs=4 "
                f"{_quote(dump_file)}"
            )
            result = subprocess.run(restore_cmd, shell=True, check=False, env=env_dst, capture_output=True, text=True)
            if result.returncode not in (0, 1):
                raise subprocess.CalledProcessError(result.returncode, restore_cmd, output=result.stdout, stderr=result.stderr)

            duracion = time.time() - t0

            db.session.add(Log(
                nivel="INFO", servicio="REPLICATION",
                mensaje=f"Réplica completa {origen['name']} -> {destino['name']} OK",
                detalle=f"dump={dump_file}, hash={hash_file}, peso={peso}, duracion={duracion:.1f}s"
            ))
            db.session.commit()

            return {
                "ok": True, "dump_file": dump_file, "hash_sha256": hash_file,
                "peso_bytes": peso, "duracion_s": duracion
            }
        except subprocess.CalledProcessError as e:
            stderr = e.stderr if e.stderr else ""
            error_msg = str(e) + (f" | stderr: {stderr[:1000]}" if stderr else " (sin stderr)")
            duracion = time.time() - t0
            db.session.add(Log(
                nivel="ERROR", servicio="REPLICATION",
                mensaje=f"Réplica completa {origen['name']} falló",
                detalle=error_msg
            ))
            db.session.commit()
            return {"ok": False, "error": error_msg, "duracion_s": duracion}

    @staticmethod
    def replicar_incremental(
        origen_conn: dict, destino_conn: dict, tablas: list,
        dias_ventana: int = 1, chunk_size: int = 1000
    ) -> dict:
        import psycopg2
        from psycopg2.extras import execute_values

        t0 = time.time()
        total_filas = 0
        resultados = []

        local_conn = psycopg2.connect(**origen_conn)
        remote_conn = psycopg2.connect(**destino_conn)

        try:
            for tbl in tablas:
                t1 = time.time()
                try:
                    columnas = ReplicationService._obtener_columnas(local_conn, tbl["origen"])
                    pk_cols = ReplicationService._obtener_pk(local_conn, tbl["origen"])

                    select_sql = ReplicationService._build_select_sql(tbl["origen"], dias_ventana)
                    upsert_sql = ReplicationService._build_upsert(tbl["destino"], columnas, pk_cols)

                    filas = 0
                    with local_conn.cursor(name=f"csr_{tbl['origen']}") as cur_src, remote_conn.cursor() as cur_dst:
                        cur_src.itersize = chunk_size
                        cur_src.execute(select_sql)
                        while True:
                            rows = cur_src.fetchmany(chunk_size)
                            if not rows:
                                break
                            execute_values(cur_dst, upsert_sql, rows, page_size=300)
                            remote_conn.commit()
                            filas += len(rows)

                    total_filas += filas
                    resultados.append({
                        "tabla": tbl["destino"], "filas": filas,
                        "duracion_s": time.time() - t1, "ok": True
                    })
                except Exception as e:
                    resultados.append({
                        "tabla": tbl.get("destino", "?"), "filas": 0,
                        "duracion_s": time.time() - t1, "ok": False, "error": str(e)
                    })

            duracion = time.time() - t0
            fallos = [r for r in resultados if not r["ok"]]
            db.session.add(Log(
                nivel="ERROR" if fallos else "INFO",
                servicio="REPLICATION",
                mensaje=f"Replicación incremental: {len(resultados)} tablas, {total_filas} filas",
                detalle=f"ok={len(resultados)-len(fallos)} err={len(fallos)} duracion={duracion:.1f}s"
            ))
            db.session.commit()
            return {"ok": len(fallos) == 0, "resultados": resultados, "total_filas": total_filas, "duracion_s": duracion}
        finally:
            local_conn.close()
            remote_conn.close()

    @staticmethod
    def _obtener_columnas(conn, tabla: str):
        schema, table = tabla.split(".")
        q = """SELECT column_name FROM information_schema.columns
               WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position"""
        with conn.cursor() as cur:
            cur.execute(q, (schema, table))
            return [r[0] for r in cur.fetchall()]

    @staticmethod
    def _obtener_pk(conn, tabla: str):
        schema, table = tabla.split(".")
        q = """SELECT kcu.column_name
               FROM information_schema.table_constraints tc
               JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name
               WHERE tc.constraint_type='PRIMARY KEY' AND tc.table_schema=%s AND tc.table_name=%s"""
        with conn.cursor() as cur:
            cur.execute(q, (schema, table))
            return [r[0] for r in cur.fetchall()]

    @staticmethod
    def _build_select_sql(origen: str, dias_ventana: int) -> str:
        if dias_ventana <= 1:
            return f"SELECT * FROM {origen} WHERE GREATEST(feccrea, COALESCE(fecmodi, feccrea)) >= date_trunc('day', now())"
        return f"SELECT * FROM {origen} WHERE GREATEST(feccrea, COALESCE(fecmodi, feccrea)) >= (CURRENT_DATE - {dias_ventana} * INTERVAL '1 day')"

    @staticmethod
    def _build_upsert(destino: str, columnas: list, pk_cols: list) -> str:
        col_list = ", ".join(columnas)
        pk_list = ", ".join(pk_cols)
        cols_update = [c for c in columnas if c not in pk_cols]
        if not cols_update:
            return f"INSERT INTO {destino} ({col_list}) VALUES %s ON CONFLICT ({pk_list}) DO NOTHING"
        set_clause = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols_update)
        return f"INSERT INTO {destino} ({col_list}) VALUES %s ON CONFLICT ({pk_list}) DO UPDATE SET {set_clause}"
