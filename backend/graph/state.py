from typing import TypedDict


class SQLAgentState(TypedDict):
    question: str
    schema: str
    schema_tables: list[str]
    schema_columns: dict[str, list[str]]
    sql: str
    tables_used: list[str]
    reasoning: str
    errors: list[str]
    error_category: str
    attempts: int
    result: list[dict]
    answer: str
    status: str
