import os
import shlex
import shutil
import sys


def quote(s: str) -> str:
    if sys.platform == "win32":
        return f'"{s}"'
    return shlex.quote(s)


def find_pg_dump() -> str:
    exe = shutil.which("pg_dump")
    if exe:
        return exe
    candidates = [
        r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\13\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\12\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\11\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\10\bin\pg_dump.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "pg_dump"


def find_pg_restore() -> str:
    exe = shutil.which("pg_restore")
    if exe:
        return exe
    candidates = [
        r"C:\Program Files\PostgreSQL\18\bin\pg_restore.exe",
        r"C:\Program Files\PostgreSQL\17\bin\pg_restore.exe",
        r"C:\Program Files\PostgreSQL\16\bin\pg_restore.exe",
        r"C:\Program Files\PostgreSQL\15\bin\pg_restore.exe",
        r"C:\Program Files\PostgreSQL\14\bin\pg_restore.exe",
        r"C:\Program Files\PostgreSQL\13\bin\pg_restore.exe",
        r"C:\Program Files\PostgreSQL\12\bin\pg_restore.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "pg_restore"
