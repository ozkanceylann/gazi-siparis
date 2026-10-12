import os
import psycopg
from psycopg.rows import dict_row

def connect():
    return psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row, connect_timeout=10, options='-c search_path=gazi_ops,pg_catalog')
