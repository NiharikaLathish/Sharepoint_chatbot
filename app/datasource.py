"""Loads tabular data into an in-memory DuckDB and auto-discovers its schema.

The source is pluggable:
  - local file (.xlsx/.csv)  -> read from disk          [use this today]
  - SharePoint (Graph API)   -> fetch the file live     [wire later]

Either way the data lands in one DuckDB table, and we read its columns straight
from the data — so the chatbot works on ANY file with no hand-written schema map.
No data is kept on disk by the app; it lives in memory for the session and is
re-fetched on restart (so a SharePoint source always reflects the latest file).
"""
import io
from functools import lru_cache

import duckdb
import pandas as pd

from .config import settings


def _load_dataframe() -> pd.DataFrame:
    if settings.source_type == "sharepoint":
        from .sharepoint import fetch_file_bytes
        raw = fetch_file_bytes(settings.sharepoint_file_url, settings.graph_token)
        return pd.read_excel(io.BytesIO(raw))
    # if settings.source_type == "gdrive":
    #     import requests
    #     url = f"https://drive.google.com/uc?export=download&id={settings.gdrive_file_id}"
    #     response = requests.get(url, allow_redirects=True)
    #     response.raise_for_status()
    #     return pd.read_excel(io.BytesIO(response.content))
    if settings.source_type == "gdrive":
        import requests

    url = f"https://drive.google.com/uc?export=download&id={settings.gdrive_file_id}"
    response = requests.get(url, allow_redirects=True)

    print("Status:", response.status_code)
    print("Content-Type:", response.headers.get("Content-Type"))

    with open("debug_download.bin", "wb") as f:
        f.write(response.content)

    raise Exception("Downloaded file saved as debug_download.bin")
    # local
    path = settings.data_path
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


@lru_cache
def get_connection() -> duckdb.DuckDBPyConnection:
    """Build an in-memory DuckDB with the source data registered as one table."""
    df = _load_dataframe()
    con = duckdb.connect(":memory:")
    con.register("_src", df)
    con.execute(f'CREATE TABLE "{settings.table_name}" AS SELECT * FROM _src')
    con.unregister("_src")
    return con


@lru_cache
def schema() -> tuple[str, frozenset[str]]:
    """Return (human-readable schema text for the prompt, set of allowed identifiers)."""
    con = get_connection()
    rows = con.execute(f'DESCRIBE "{settings.table_name}"').fetchall()
    cols = [(r[0], r[1]) for r in rows]  # (name, type)
    lines = [f'TABLE: "{settings.table_name}"', "COLUMNS:"]
    for name, dtype in cols:
        lines.append(f'  "{name}" ({dtype})')
    allowed = {settings.table_name} | {name for name, _ in cols}
    return "\n".join(lines), frozenset(allowed)


def run_sql(sql: str) -> list[dict]:
    con = get_connection()
    cur = con.execute(sql)
    columns = [d[0] for d in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]
