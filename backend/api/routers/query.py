import asyncio

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from backend.database.connection import readonly_engine
from backend.database.schema import reflect_schema
from backend.llm.client import SQLResponse, get_llm

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    sql: str
    tables_used: list[str]
    reasoning: str
    rows: list[dict]


def format_schema(tables: dict) -> str:
    lines = []
    for table_name, columns in tables.items():
        col_descriptions = ", ".join(
            f"{c['name']} {c['type']}" + (f" -> {c['foreign_key']}" if c["foreign_key"] else "")
            for c in columns
        )
        lines.append(f"{table_name}({col_descriptions})")
    return "\n".join(lines)


def run_query(sql: str) -> list[dict]:
    with readonly_engine.connect() as conn:
        return [dict(row._mapping) for row in conn.execute(text(sql))]


@router.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    schema_text = format_schema(await asyncio.to_thread(reflect_schema))
    prompt = (
        f"Database schema:\n{schema_text}\n\n"
        f"Question: {request.question}\n\n"
        "Write a single read-only SQL query (SELECT or WITH ... SELECT only) "
        "that answers the question using only the tables and columns above."
    )
    structured_llm = get_llm().with_structured_output(SQLResponse)
    result: SQLResponse = await structured_llm.ainvoke(prompt)

    rows = await asyncio.to_thread(run_query, result.sql)

    return QueryResponse(**result.model_dump(), rows=rows)


if __name__ == "__main__":
    response = asyncio.run(query(QueryRequest(question="How many tracks are in the database?")))
    assert response.sql
    assert len(response.rows) > 0
    print(response)
