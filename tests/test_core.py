"""Tests that run with a small generated Excel and a mocked LLM (no network)."""
import asyncio

import pandas as pd
import pytest


@pytest.fixture(scope="module", autouse=True)
def _sample_data(tmp_path_factory):
    """Create a tiny HR Excel and point settings at it before app imports use it."""
    d = tmp_path_factory.mktemp("data")
    path = d / "staff.xlsx"
    pd.DataFrame({
        "Emp ID": [1, 2, 3, 4],
        "Job Title": ["Engineer", "Engineer", "Analyst", "Manager"],
        "Gender": ["Female", "Male", "Female", "Male"],
        "Salary": [80000, 75000, 60000, 95000],
    }).to_excel(path, index=False)

    from app.config import settings
    settings.data_path = str(path)
    settings.table_name = "staff"
    # reset cached connection/schema if already built
    from app import datasource
    datasource.get_connection.cache_clear()
    datasource.schema.cache_clear()
    yield


def test_schema_autodiscovers_columns():
    from app.datasource import schema
    text, allowed = schema()
    assert "Salary" in allowed and "Job Title" in allowed and "staff" in allowed
    assert "Salary" in text


def test_run_sql_aggregates():
    from app.datasource import run_sql
    rows = run_sql('SELECT AVG("Salary") AS avg_salary FROM "staff"')
    assert round(rows[0]["avg_salary"]) == 77500


def test_sql_validator_blocks_writes():
    from app.sql_validate import SqlValidationError, validate_sql
    validate_sql('SELECT * FROM "staff"')
    for bad in ['DROP TABLE "staff"', 'UPDATE "staff" SET "Salary"=0',
                'SELECT 1; DROP TABLE "staff"']:
        with pytest.raises(SqlValidationError):
            validate_sql(bad)


def test_agent_happy_path(monkeypatch):
    from app import agent

    async def fake_complete(system, user, temperature=0.1):
        if "translate a business question" in system:
            return 'SELECT "Job Title", AVG("Salary") AS avg_salary FROM "staff" GROUP BY "Job Title" ORDER BY avg_salary DESC'
        if "explain SQL query results" in system:
            return "Managers have the highest average salary."
        return user

    monkeypatch.setattr(agent.llm, "complete", fake_complete)
    res = asyncio.run(agent.answer_question("avg salary by job title", []))
    assert "Managers" in res.answer
    assert res.rows and any(r["avg_salary"] == 95000 for r in res.rows)
    assert res.explainability.confidence == "high"


def test_agent_refuses_on_bad_column(monkeypatch):
    from app import agent

    async def fake_complete(system, user, temperature=0.1):
        return 'SELECT AVG("Bonus") FROM "staff"'  # no such column

    monkeypatch.setattr(agent.llm, "complete", fake_complete)
    res = asyncio.run(agent.answer_question("average bonus?", []))
    assert res.answer == agent.REFUSAL
