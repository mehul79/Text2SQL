import asyncio

from backend.database.connection import run_query
from backend.database.schema import format_schema, reflect_schema
from backend.graph.state import SQLAgentState
from backend.llm.client import SQLResponse, get_structured_llm
from backend.security.sql_guard import validate_sql

MAX_REPAIR_ATTEMPTS = 3

# backstop above the DB's own statement_timeout (backend/database/connection.py) —
# if that layer ever fails to fire (driver hang, network stall), the app still cuts
# the query off rather than blocking the graph indefinitely.
QUERY_WALL_CLOCK_SECONDS = 10

# error_category -> hint injected into the repair prompt (PRD §16). Matched
# against the raw message from sql_guard (validate) or Postgres (execute_sql).
_CATEGORY_MATCHERS = [
    ("unknown_table", lambda e: "unknown table" in e or ("relation" in e and "does not exist" in e)),
    ("unknown_column", lambda e: "column" in e),
    ("syntax_error", lambda e: "syntax error" in e),
    ("permission_denied", lambda e: "permission denied" in e),
    ("disallowed_operation", lambda e: any(
        k in e for k in ("disallowed operation", "only select", "single sql statement")
    )),
    ("timeout", lambda e: "wall-clock limit" in e or "timeout" in e),
]

_CATEGORY_HINTS = {
    "unknown_table": "The table name is wrong. Use the exact table name from the schema "
    "(check singular vs plural, casing) instead of a common-convention guess.",
    "unknown_column": "The column name is wrong or on the wrong table. Use the exact "
    "column name for that table from the schema.",
    "syntax_error": "The SQL has a syntax error. Rewrite it as valid PostgreSQL.",
    "permission_denied": "The query reached something outside read access. Use only "
    "SELECT / WITH ... SELECT on the tables in the schema.",
    "disallowed_operation": "The query used a write or DDL operation. Rewrite it as a "
    "read-only SELECT or WITH ... SELECT.",
    "timeout": "The query took too long, likely scanning far more rows than the question "
    "needs. Add a LIMIT, narrow the WHERE clause, or aggregate instead of returning raw rows.",
    "unknown": "Diagnose the error message below and correct the query.",
}


def classify_error(error: str) -> str:
    lowered = error.lower()
    for category, matches in _CATEGORY_MATCHERS:
        if matches(lowered):
            return category
    return "unknown"


def understand(state: SQLAgentState) -> dict:
    return {"errors": [], "attempts": 0}


async def retrieve_schema(state: SQLAgentState) -> dict:
    tables = await asyncio.to_thread(reflect_schema)
    return {
        "schema": format_schema(tables),
        "schema_tables": list(tables.keys()),
        "schema_columns": {name: [c["name"] for c in cols] for name, cols in tables.items()},
    }


async def generate_sql(state: SQLAgentState) -> dict:
    prompt = (
        f"Database schema:\n{state['schema']}\n\n"
        f"Question: {state['question']}\n\n"
        "Write a single read-only SQL query (SELECT or WITH ... SELECT only) "
        "that answers the question using only the tables and columns above."
    )
    result: SQLResponse = await get_structured_llm().ainvoke(prompt)
    return {"sql": result.sql, "tables_used": result.tables_used, "reasoning": result.reasoning}


def validate(state: SQLAgentState) -> dict:
    known_tables = {t.lower() for t in state["schema_tables"]}
    known_columns = {t.lower(): {c.lower() for c in cols} for t, cols in state["schema_columns"].items()}
    errors = validate_sql(state["sql"], known_tables=known_tables, known_columns=known_columns)
    return {"errors": errors}


async def execute_sql(state: SQLAgentState) -> dict:
    try:
        rows = await asyncio.wait_for(
            asyncio.to_thread(run_query, state["sql"]), timeout=QUERY_WALL_CLOCK_SECONDS
        )
        return {"result": rows, "errors": []}
    except TimeoutError:
        return {"errors": [f"query exceeded the {QUERY_WALL_CLOCK_SECONDS}s wall-clock limit"]}
    except Exception as e:
        return {"errors": [f"database error: {e}"]}


def diagnose_error(state: SQLAgentState) -> dict:
    return {"error_category": classify_error(state["errors"][-1])}


async def repair_sql(state: SQLAgentState) -> dict:
    hint = _CATEGORY_HINTS[state.get("error_category", "unknown")]
    prompt = (
        f"Database schema:\n{state['schema']}\n\n"
        f"Question: {state['question']}\n\n"
        f"Previous SQL attempt:\n{state['sql']}\n\n"
        f"That query failed with:\n{state['errors'][-1]}\n\n"
        f"Diagnosis: {hint}\n\n"
        "Write a corrected single read-only SQL query (SELECT or WITH ... SELECT only) "
        "that fixes the problem above, using only the tables and columns in the schema."
    )
    result: SQLResponse = await get_structured_llm().ainvoke(prompt)
    return {
        "sql": result.sql,
        "tables_used": result.tables_used,
        "reasoning": result.reasoning,
        "attempts": state["attempts"] + 1,
    }


def respond(state: SQLAgentState) -> dict:
    if state["errors"]:
        return {
            "status": "failed",
            "answer": (
                f"Unable to generate a valid query after {state['attempts']} repair attempt(s). "
                f"Last error: {state['errors'][-1]}"
            ),
        }
    return {"status": "ok", "answer": f"Query returned {len(state['result'])} row(s)."}


if __name__ == "__main__":
    assert classify_error('unknown table: customers') == "unknown_table"
    assert classify_error('relation "customers" does not exist') == "unknown_table"
    assert classify_error('column "titel" does not exist') == "unknown_column"
    assert classify_error("syntax error at or near SELCT") == "syntax_error"
    assert classify_error("permission denied for table employee") == "permission_denied"
    assert classify_error("disallowed operation: Delete") == "disallowed_operation"
    assert classify_error(f"query exceeded the {QUERY_WALL_CLOCK_SECONDS}s wall-clock limit") == "timeout"
    assert classify_error("something unrecognised") == "unknown"
    print("classify_error self-check passed")
