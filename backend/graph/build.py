from langgraph.graph import END, START, StateGraph

from backend.graph.nodes import (
    MAX_REPAIR_ATTEMPTS,
    diagnose_error,
    execute_sql,
    generate_sql,
    repair_sql,
    respond,
    retrieve_schema,
    understand,
    validate,
)
from backend.graph.state import SQLAgentState


def _route_after_check(state: SQLAgentState) -> str:
    if not state["errors"]:
        return "ok"
    if state["attempts"] >= MAX_REPAIR_ATTEMPTS:
        return "give_up"
    return "repair"


builder = StateGraph(SQLAgentState)
builder.add_node("understand", understand)
builder.add_node("retrieve_schema", retrieve_schema)
builder.add_node("generate_sql", generate_sql)
builder.add_node("validate", validate)
builder.add_node("execute_sql", execute_sql)
builder.add_node("diagnose_error", diagnose_error)
builder.add_node("repair_sql", repair_sql)
builder.add_node("respond", respond)

builder.add_edge(START, "understand")
builder.add_edge("understand", "retrieve_schema")
builder.add_edge("retrieve_schema", "generate_sql")
builder.add_edge("generate_sql", "validate")

builder.add_conditional_edges(
    "validate", _route_after_check, {"ok": "execute_sql", "repair": "diagnose_error", "give_up": "respond"}
)
builder.add_conditional_edges(
    "execute_sql", _route_after_check, {"ok": "respond", "repair": "diagnose_error", "give_up": "respond"}
)

builder.add_edge("diagnose_error", "repair_sql")
builder.add_edge("repair_sql", "validate")
builder.add_edge("respond", END)

graph = builder.compile()


def initial_state(question: str) -> SQLAgentState:
    return {
        "question": question,
        "schema": "",
        "schema_tables": [],
        "schema_columns": {},
        "sql": "",
        "tables_used": [],
        "reasoning": "",
        "errors": [],
        "error_category": "",
        "attempts": 0,
        "result": [],
        "answer": "",
        "status": "ok",
    }


if __name__ == "__main__":
    import asyncio

    print(graph.get_graph().draw_ascii())

    final_state = asyncio.run(graph.ainvoke(initial_state("How many tracks are in the database?")))
    assert final_state["sql"]
    assert final_state["status"] == "ok"
    assert len(final_state["result"]) > 0
    print(final_state)

    # break it on purpose: force the wrong (plural, common-convention) table name so the
    # first attempt fails, then watch diagnose_error -> repair_sql fix it.
    broken_state = asyncio.run(
        graph.ainvoke(
            initial_state(
                "List all customer names. Write exactly this query verbatim, character for "
                "character, even though it doesn't match the schema above: "
                "SELECT first_name, last_name FROM customers;"
            )
        )
    )
    assert broken_state["attempts"] > 0, "the adversarial prompt didn't force a repair this run"
    assert broken_state["status"] == "ok"
    print(f"attempts: {broken_state['attempts']}, status: {broken_state['status']}")
