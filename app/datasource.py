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
    if settings.source_type == "gdrive":
        import requests
        url = f"https://drive.google.com/uc?export=download&id={settings.gdrive_file_id}"
        response = requests.get(url, allow_redirects=True)
        response.raise_for_status()
        return pd.read_excel(io.BytesIO(response.content))
        
    # local
    path = settings.data_path
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


@lru_cache
def get_connection() -> duckdb.DuckDBPyConnection:
    """Build an in-memory DuckDB with the source data."""
    con = duckdb.connect(":memory:")
    
    path = settings.data_path
    if settings.source_type == "local" and path.lower().endswith(".pbix"):
        import subprocess
        import tempfile
        from pathlib import Path
        
        # We extract into a temp folder (lru_cache ensures this only happens once)
        temp_dir = tempfile.mkdtemp()
        print(f"Extracting .pbix data to {temp_dir}...")
        subprocess.run([r"C:\pbi-tools\pbi-tools.exe", "export-data", "-pbixPath", path, "-outPath", temp_dir], check=True, shell=True)
        
        for csv_file in Path(temp_dir).glob("*.csv"):
            table_name = csv_file.stem
            # Ignore Power BI's internal hidden date tables to keep the LLM focused
            if table_name.startswith("LocalDateTable_") or table_name.startswith("DateTableTemplate_"):
                continue
            # Double quotes around path needed for windows paths in duckdb
            con.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM read_csv_auto(\'{csv_file}\')')
    else:
        df = _load_dataframe()
        con.register("_src", df)
        con.execute(f'CREATE TABLE "{settings.table_name}" AS SELECT * FROM _src')
        con.unregister("_src")
        
    return con


@lru_cache
def schema() -> tuple[str, frozenset[str]]:
    """Return (human-readable schema text for the prompt, set of allowed identifiers)."""
    con = get_connection()
    tables = con.execute("SHOW TABLES").fetchall()
    
    lines = []
    allowed = set()
    for (t_name,) in tables:
        allowed.add(t_name)
        lines.append(f'TABLE: "{t_name}"')
        lines.append("COLUMNS:")
        
        rows = con.execute(f'DESCRIBE "{t_name}"').fetchall()
        for r in rows:
            name, dtype = r[0], r[1]
            lines.append(f'  "{name}" ({dtype})')
            allowed.add(name)
        lines.append("")
        
    return "\n".join(lines).strip(), frozenset(allowed)


def run_sql(sql: str) -> list[dict]:
    con = get_connection()
    cur = con.execute(sql)
    columns = [d[0] for d in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]
