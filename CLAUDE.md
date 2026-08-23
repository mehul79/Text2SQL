# CLAUDE.md

A **learning project**, not a production build. Full spec:
`PRD — Self-Healing Text-to-SQL Assistant.md` — the north star for *what* the
system eventually does. Ignore its observability/eval/MLOps ambitions
(sections 21-28) until the fundamentals below work. Optimize for the user
understanding every piece, not for finishing fast.

## Learning goals, in build order

1. **Python module routing** — packages, `__init__.py`, absolute vs relative
   imports, `python -m` vs script execution, why imports break.
2. **FastAPI** — Pydantic request/response models, path/query/body params,
   `Depends`, routers, `/docs`.
3. **Model/provider routing** — swap LLM provider via env config, not code
   (PRD §25).
4. **async/asyncio** — what actually runs concurrently vs. merely looks async;
   sync DB/LLM calls blocking the event loop; `gather`, `to_thread`.
5. **LangGraph** — nodes, conditional edges, typed shared state, bounded
   loops. The self-healing retry loop (PRD §10-15) is the point of the project.
6. **SQLAlchemy** — engine/session lifecycle, pooling, Core vs ORM, reflecting
   an existing schema.

Frontend (websockets, streaming, custom + AI component libraries) is a
**later phase**. Do not scaffold frontend code until the user starts it.

## Workflow: notebook → module

- New concept → prototype in `notebooks/NN-topic.ipynb` first. Messy,
  cell-by-cell, print-driven is fine there.
- Once understood, port the cleaned version into `backend/`. Notebook habits
  (hardcoded values, no error handling, bare excepts) don't cross that line.
- Ported non-trivial logic leaves **one runnable check** behind — an
  `assert`-based `if __name__ == "__main__":` block or a small `test_*.py`.
  No test frameworks/fixtures beyond that.
- Create a module when there's real code for it. No stub files or empty
  folders for future phases.

## Layout

Grows as we go; nothing pre-built:

```
notebooks/          NN-topic.ipynb, numbered in learning order
backend/            ported, cleaned modules (mirrors PRD §33 loosely)
.env / .env.example config — never commit .env
```

## Toolchain (Windows / PowerShell)

- `.venv` + pip, `requirements.txt`. Activate:
  `.\.venv\Scripts\Activate.ps1`
- Run the API: `uvicorn backend.api.main:app --reload` from the repo root, so
  `backend` resolves as a package (this is learning goal 1 in practice).
- Notebooks use the `.venv` kernel — not a global Python. Import failures in
  notebooks are usually kernel-vs-venv mismatch or cwd, not bad code.
- Install only what the current phase needs. No pgvector / LangSmith /
  OpenTelemetry / sqlglot until we reach that phase.

## Phase gating (PRD §34)

Baseline (question → SQL → read-only execute → result) **before** LangGraph
**before** self-healing/repair **before** security hardening **before**
eval. Don't build retries before a working single-pass version exists.

## Non-negotiables from day one

- **Read-only DB role**, even in the first notebook. Never connect as
  superuser/owner.
- **The LLM is never the security boundary.** SELECT / `WITH ... SELECT`
  allowlisting lives in application code, testable in isolation, independent
  of any prompt.
- Credentials and model config via env vars only. Never hardcoded, never in a
  notebook cell, never sent to the LLM.

## Git

- Never add any Claude/AI attribution to commits — no `Co-Authored-By:
  Claude`, no "generated with Claude Code" trailer, no such flag or footer of
  any kind. Commits are authored as the user, plain and unmarked.

## Teaching style

- Small runnable example first, short explanation after. Not the reverse.
- Say *why* this tool over the obvious alternative — LangGraph over a `while`
  loop, SQLAlchemy over raw `psycopg2`, async over threads.
- Name boilerplate as boilerplate and move on.
- Always render the compiled LangGraph before running it:
  `graph.get_graph().draw_ascii()` (no deps) or `.draw_mermaid_png()` (needs
  network/graphviz — fall back to ascii rather than debugging renderers).
