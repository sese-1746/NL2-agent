from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "demo.db"


def init_database(path: Path = DB_PATH) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_DIR / "demo.csv"
    if not csv_path.exists():
        return
    if path.exists():
        with sqlite3.connect(path) as conn:
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='orders'").fetchone()
        if exists:
            return
    df = pd.read_csv(csv_path)
    with sqlite3.connect(path) as conn:
        df.to_sql("orders", conn, if_exists="replace", index=False)


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    init_database(path)
    return sqlite3.connect(path)


def get_schema(path: Path = DB_PATH) -> Dict[str, list]:
    with connect(path) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        schema = {}
        for (table,) in tables:
            rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
            schema[table] = [{"name": row[1], "type": row[2], "description": ""} for row in rows]
        return schema
