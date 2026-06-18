"""SQL safety gate.

The grounding guarantee: the LLM emits a read-only SELECT; DuckDB computes the
numbers from real data; the LLM only explains them. This gate makes sure the
generated SQL can't do anything except read.
"""
import re

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|COPY|INSTALL|"
    r"LOAD|PRAGMA|EXPORT|IMPORT|CALL|SET|REPLACE|TRUNCATE)\b",
    re.IGNORECASE,
)


class SqlValidationError(ValueError):
    pass


def validate_sql(sql: str) -> None:
    s = sql.strip().rstrip(";").strip()
    if not s:
        raise SqlValidationError("Empty query.")
    if ";" in s:
        raise SqlValidationError("Only a single statement is allowed.")
    if not re.match(r"^(SELECT|WITH)\b", s, re.IGNORECASE):
        raise SqlValidationError("Only read-only SELECT queries are permitted.")
    if _FORBIDDEN.search(s):
        raise SqlValidationError("Query contains a non-read-only keyword.")
