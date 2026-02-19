import sqlite3
import importlib
import json

config = importlib.import_module('src.config')
db_path = config.DB_PATH
print('DB_PATH:', db_path)
conn = sqlite3.connect(db_path)
cur = conn.cursor()
try:
    cur.execute("PRAGMA table_info(dives)")
    rows = cur.fetchall()
    print('dives schema:')
    print(json.dumps(rows, indent=2))
except Exception as e:
    print('error:', e)
finally:
    conn.close()
