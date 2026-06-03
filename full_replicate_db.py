#!/usr/bin/env python3
"""
full_replicate_db.py
Replica completa de una base PostgreSQL (estructura + datos)
usando pg_dump/pg_restore.

Uso típico:
  python full_replicate_db.py --confirm

Variables de entorno esperadas:
  SRC_DB_HOST, SRC_DB_PORT, SRC_DB_NAME, SRC_DB_USER, SRC_DB_PASSWORD
  DST_DB_HOST, DST_DB_PORT, DST_DB_NAME, DST_DB_USER, DST_DB_PASSWORD

Opcionales:
  DUMP_DIR (default: /tmp)
"""

import os
import shlex
import subprocess
import tempfile
from datetime import datetime
import argparse


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def run(cmd: str, env_vars=None):
    print(f"$ {cmd}")
    subprocess.run(cmd, shell=True, check=True, env=env_vars)


def main():
    p = argparse.ArgumentParser(description="Replica completa PostgreSQL via pg_dump/pg_restore")
    p.add_argument("--confirm", action="store_true", help="Confirmar ejecución destructiva en destino")
    p.add_argument("--jobs", type=int, default=4, help="Paralelismo pg_restore")
    args = p.parse_args()

    src = {
        "host": env("SRC_DB_HOST", "192.168.0.88"),
        "port": env("SRC_DB_PORT", "5432"),
        "name": env("SRC_DB_NAME", "ErpEpmapaT"),
        "user": env("SRC_DB_USER", "postgres"),
        "password": env("SRC_DB_PASSWORD", ""),
    }
    dst = {
        "host": env("DST_DB_HOST", "66.85.156.59"),
        "port": env("DST_DB_PORT", "5432"),
        "name": env("DST_DB_NAME", "ErpEpmapaT"),
        "user": env("DST_DB_USER", "postgres"),
        "password": env("DST_DB_PASSWORD", ""),
    }

    missing = [k for k, v in {**{f'SRC_{x.upper()}': src[x] for x in src}, **{f'DST_{x.upper()}': dst[x] for x in dst}}.items() if not v]
    if missing:
        raise SystemExit(f"Faltan variables: {', '.join(missing)}")

    if not args.confirm:
        raise SystemExit("Este proceso reemplaza objetos en destino. Ejecuta con --confirm")

    dump_dir = env("DUMP_DIR", "/tmp")
    os.makedirs(dump_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = os.path.join(dump_dir, f"{src['name']}_full_{ts}.dump")

    env_src = os.environ.copy()
    env_src["PGPASSWORD"] = src["password"]

    env_dst = os.environ.copy()
    env_dst["PGPASSWORD"] = dst["password"]

    dump_cmd = (
        f"pg_dump -h {shlex.quote(src['host'])} -p {shlex.quote(src['port'])} "
        f"-U {shlex.quote(src['user'])} -d {shlex.quote(src['name'])} "
        f"-Fc -f {shlex.quote(dump_file)}"
    )

    restore_cmd = (
        f"pg_restore -h {shlex.quote(dst['host'])} -p {shlex.quote(dst['port'])} "
        f"-U {shlex.quote(dst['user'])} -d {shlex.quote(dst['name'])} "
        f"--clean --if-exists --no-owner --no-privileges --jobs={args.jobs} "
        f"{shlex.quote(dump_file)}"
    )

    print("=== REPLICA COMPLETA ===")
    print(f"Origen : {src['host']}:{src['port']}/{src['name']}")
    print(f"Destino: {dst['host']}:{dst['port']}/{dst['name']}")
    print(f"Dump   : {dump_file}")

    run(dump_cmd, env_src)
    run(restore_cmd, env_dst)

    print("✅ Replica completa finalizada")
    print(f"Archivo dump: {dump_file}")


if __name__ == "__main__":
    main()
