import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.graph.build import graph, initial_state

router = APIRouter()

# One question can cost several LLM calls: generate, then up to MAX_REPAIR_ATTEMPTS
# repairs. 30s only ever fit the questions that got it right first try.
REQUEST_TIMEOUT_SECONDS = 150

# ponytail: in-memory dict — fine for a single dev process, swap for a real
# store (Postgres table, Redis) if this needs to survive a restart or scale out.
_STORE: dict[str, "QueryResponse"] = {}


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    query_id: str
    sql: str
    tables_used: list[str]
    reasoning: str
    rows: list[dict]
    status: str
    attempts: int
    answer: str


async def _run_graph(question: str):
    try:
        return await asyncio.wait_for(graph.ainvoke(initial_state(question)), timeout=REQUEST_TIMEOUT_SECONDS)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="query timed out")
    except Exception as e:
        # the LLM provider is the usual culprit here; surface it instead of a bare 500
        raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {e}")


@router.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    final_state = await _run_graph(request.question)
    response = QueryResponse(
        query_id=str(uuid.uuid4()),
        sql=final_state["sql"],
        tables_used=final_state["tables_used"],
        reasoning=final_state["reasoning"],
        rows=final_state["result"],
        status=final_state["status"],
        attempts=final_state["attempts"],
        answer=final_state["answer"],
    )
    _STORE[response.query_id] = response
    return response


@router.get("/api/query/{query_id}", response_model=QueryResponse)
async def get_query(query_id: str):
    response = _STORE.get(query_id)
    if response is None:
        raise HTTPException(status_code=404, detail="query not found")
    return response


@router.post("/api/query/stream")
async def query_stream(request: QueryRequest):
    async def events():
        async for update in graph.astream(initial_state(request.question), stream_mode="updates"):
            for node_name, node_output in update.items():
                yield f"data: {json.dumps({'node': node_name, 'data': node_output}, default=str)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


if __name__ == "__main__":
    response = asyncio.run(query(QueryRequest(question="How many tracks are in the database?")))
    assert response.sql
    assert response.status == "ok"
    assert len(response.rows) > 0
    stored = asyncio.run(get_query(response.query_id))
    assert stored.query_id == response.query_id
    print(response)
