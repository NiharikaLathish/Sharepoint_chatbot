"""The grounded agent (Option B: SharePoint/file data via SQL).

    rewrite (if history) -> generate SQL -> validate -> execute -> explain

Same invariant as the Power BI version: the LLM emits a query, the engine
(DuckDB) computes the numbers from real data, and the LLM only explains them.
On any unrecoverable failure we return the fixed refusal rather than guess.
"""
import datetime as dt
import re

from . import llm
from .config import settings
from .datasource import run_sql, schema
from .models import ChatResponse, Explainability, Turn
from .prompts import EXPLAIN_SYSTEM, GENERATE_SYSTEM, REFUSAL, REWRITE_SYSTEM
from .sql_validate import SqlValidationError, validate_sql

_MAX_RETRIES = 1
_FENCE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _clean(raw: str) -> str:
    return _FENCE.sub("", raw).strip().rstrip(";")


async def _rewrite(message: str, history: list[Turn]) -> str:
    if not history:
        return message
    convo = "\n".join(f"  {t.role}: {t.content}" for t in history)
    return await llm.complete(
        REWRITE_SYSTEM, f"History:\n{convo}\nFollow-up: {message}\nRewritten:", 0.0
    )


async def _generate(question: str) -> str:
    schema_text, _ = schema()
    system = GENERATE_SYSTEM.format(schema=schema_text)
    return _clean(await llm.complete(system, f"Q: {question}\nA:", 0.0))


async def _explain(question: str, rows: list[dict]) -> str:
    return await llm.complete(
        EXPLAIN_SYSTEM, f"QUESTION: {question}\nRESULTS: {rows}", 0.1
    )


def _refuse(reason: str = "") -> ChatResponse:
    return ChatResponse(
        answer=REFUSAL,
        explainability=Explainability(
            source_name=settings.data_path if settings.source_type == "local"
            else "SharePoint",
            data_source=f"{settings.source_type} (DuckDB SQL)",
            query_timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
            confidence="low",
            sql=reason or None,
        ),
        rows=None,
    )


async def answer_question(message: str, history: list[Turn]) -> ChatResponse:
    question = await _rewrite(message, history)

    sql = ""
    rows: list[dict] | None = None
    confidence = "high"
    attempts = 0

    while attempts <= _MAX_RETRIES:
        attempts += 1
        sql = await _generate(question)
        try:
            validate_sql(sql)
        except SqlValidationError:
            confidence = "medium"
            continue
        try:
            rows = run_sql(sql)
        except Exception:  # noqa: BLE001 - bad column/syntax -> retry then refuse
            confidence = "medium"
            rows = None
            continue
        if rows:
            break
        confidence = "medium"

    if not rows:
        return _refuse("No rows / query failed after retries.")

    explanation = await _explain(question, rows)
    return ChatResponse(
        answer=explanation,
        explainability=Explainability(
            source_name=settings.data_path if settings.source_type == "local"
            else "SharePoint",
            data_source=f"{settings.source_type} (DuckDB SQL)",
            query_timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
            sql=sql,
            confidence=confidence,
        ),
        rows=rows,
    )
