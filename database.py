import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path("data/store.sqlite")

def execute_query(sql):
    with closing(sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        cursor = db.execute(sql)
        rows = cursor.fetchall()
        return {"columns": [column[0] for column in cursor.description], "rows": rows}
