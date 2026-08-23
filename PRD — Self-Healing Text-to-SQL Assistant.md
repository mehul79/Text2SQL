# Self-Healing Text-to-SQL Assistant

**Document Type:** Product Requirements Document  
**Version:** 1.0  
**Status:** Proposed  
**Primary Stack:** Python, LangChain, LangGraph, FastAPI, PostgreSQL, SQLAlchemy, React.js  
**Future Scope:** LangSmith / OpenTelemetry, LLM evaluation, model fine-tuning, MLOps

---

## 1. Product Overview

The **Self-Healing Text-to-SQL Assistant** is an agentic system that allows users to query structured databases using natural language.

The system converts a business question into SQL, validates the generated query against the database schema, executes it using a strictly read-only database connection, detects SQL or execution failures, automatically diagnoses and repairs the query, and returns both the result and an understandable explanation.

Unlike a basic Text-to-SQL pipeline:

> Natural Language → LLM → SQL → Database

the proposed system uses a **LangGraph-based iterative workflow**:

> Natural Language → Schema Understanding → SQL Generation → Validation → Safe Execution → Error Diagnosis → SQL Repair → Re-execution → Result Validation → Response

The core objective is **reliable Text-to-SQL generation rather than one-shot SQL generation**.

---

# 2. Problem Statement

Traditional Text-to-SQL systems frequently fail for reasons beyond simple SQL syntax:

- Incorrect table or column selection
- Missing joins
- Incorrect join relationships
- Incorrect aggregations
- Ambiguous business terminology
- SQL dialect differences
- Invalid SQL syntax
- Database execution errors
- Queries that are technically valid but semantically incorrect
- Hallucinated tables or columns
- Queries that are computationally expensive or unsafe

A production-oriented system should therefore be capable of **detecting, explaining, and recovering from failures** rather than assuming the first generated query is correct.

---

# 3. Goals

## Primary Goals

1. Convert natural-language business questions into executable SQL.
2. Ground SQL generation in the actual database schema.
3. Prevent hallucinated tables and columns.
4. Validate SQL before execution.
5. Allow database access only through a **read-only database user/role**.
6. Detect SQL execution failures automatically.
7. Diagnose and repair failed queries using an LLM agent.
8. Retry failed queries within a bounded retry budget.
9. Validate the returned result before presenting it to the user.
10. Maintain the complete execution state within a LangGraph workflow.
11. Provide transparent visibility into the generated SQL, corrections, and execution status.
12. Create a foundation for model evaluation, observability, and future fine-tuning.

## Secondary Goals

- Support multiple database engines in the future.
- Support multi-turn analytical conversations.
- Compare different LLMs and prompting strategies.
- Measure accuracy, latency, cost, and recovery rate.
- Provide production-grade observability.

---

# 4. Non-Goals for V1

The first version will not attempt to:

- Modify database data.
- Execute `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, or similar statements.
- Automatically modify database schemas.
- Fine-tune a model as part of the initial implementation.
- Support every SQL dialect simultaneously.
- Replace a full enterprise BI platform.
- Guarantee correctness for ambiguous business questions without sufficient context.

---

# 5. Target Users

### Primary User

A technical or non-technical business user who needs to obtain information from structured databases without manually writing SQL.

Example:

> "What were the top five products by revenue in Delhi last quarter?"

### Secondary User

A developer, data engineer, or analyst who wants to inspect how an AI system generates, validates, executes, and repairs SQL.

---

# 6. Example User Experience

User:

> "Show me the top 5 products by revenue in Delhi in 2025."

System internally performs:

```text
User Question
      ↓
Analyze Intent
      ↓
Retrieve Relevant Schema
      ↓
Identify Tables / Columns
      ↓
Generate SQL
      ↓
Validate SQL
      ↓
Security Check
      ↓
Execute
      ↓
Result Valid?
      ↓
Generate Answer
```

If execution fails:

```text
Generate SQL
      ↓
Execute
      ↓
Database Error
      ↓
Diagnose Error
      ↓
Repair SQL
      ↓
Validate Again
      ↓
Execute Again
      ↓
Return Result
```

The user can see:

```text
Question
"Top 5 products by revenue in Delhi"

Generated SQL
SELECT ...

Status
✓ Validated
✓ Executed successfully

Retries
1

Result
Product A   ₹12.3M
Product B   ₹10.8M
...
```

---

# 7. Functional Requirements

## FR-01: Natural Language Querying

The system shall accept natural-language questions through a REST API and React frontend.

Example:

```text
"How much revenue did each region generate in Q1?"
```

---

## FR-02: Database Connection

All database interactions shall be performed using **SQLAlchemy**.

SQLAlchemy will act as the database abstraction and connection layer, allowing the application to avoid coupling the LangGraph logic directly to a database driver.

Initial database:

```text
PostgreSQL
```

Future support:

```text
MySQL
SQL Server
SQLite
Snowflake
BigQuery
```

The database connection configuration shall be managed through environment variables/secrets rather than hard-coded credentials.

---

## FR-03: Read-Only Database Access

The application **must never have write access to the production/data database**.

The system shall use a dedicated database user/role with only the minimum required permissions, ideally:

```sql
GRANT CONNECT ON DATABASE ...
GRANT USAGE ON SCHEMA ...
GRANT SELECT ON ALL TABLES ...
```

The application must reject statements containing write or destructive operations such as:

```text
INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
CREATE
GRANT
REVOKE
```

The security layer must operate independently of the LLM.

**Important principle:**

> The LLM should never be trusted as the security mechanism.

SQL generated by the LLM must pass application-level validation before reaching the database.

---

# 8. Schema Intelligence

Before SQL generation, the agent shall identify the schema information relevant to the user's question.

Schema context may include:

```text
Database
Schema
Table
Column
Data Type
Primary Key
Foreign Key
Relationships
Column Description
Sample Values
```

Example:

```text
orders
 ├── id
 ├── customer_id → customers.id
 ├── order_date
 └── total_amount

customers
 ├── id
 ├── name
 └── region
```

The system should avoid sending the entire database schema to the LLM when unnecessary.

Future versions may use a **schema retrieval layer** using embeddings and/or pgvector to retrieve the most relevant schema elements.

---

# 9. Business Semantic Layer

The system should support business-specific definitions that cannot reliably be inferred from raw database schemas.

Example:

```text
Revenue =
SUM(order_items.quantity * order_items.unit_price)

Active Customer =
Customer with at least one completed order within 90 days

North India =
Delhi + Haryana + Punjab + Rajasthan + Uttar Pradesh + ...
```

This information may be stored as structured metadata and retrieved alongside the relevant database schema.

This reduces semantic errors where SQL is syntactically valid but answers the wrong business question.

---

# 10. LangGraph Agent Architecture

The system shall use **LangGraph** as the orchestration layer.

### Proposed graph

```text
                    START
                      │
                      ▼
             Query Understanding
                      │
                      ▼
              Schema Retrieval
                      │
                      ▼
          Business Context Retrieval
                      │
                      ▼
               SQL Generation
                      │
                      ▼
               SQL Validation
                /           \
            Invalid          Valid
              │                │
              ▼                ▼
          SQL Repair      Security Check
              │                │
              └───────►────────┘
                               │
                               ▼
                         Execute SQL
                         /         \
                      Error       Success
                       │             │
                       ▼             ▼
                Diagnose Error   Result Check
                       │             │
                       ▼             │
                  Repair SQL        │
                       │             │
                       └──────►──────┘
                                     │
                                     ▼
                             Generate Response
                                     │
                                     ▼
                                    END
```

---

# 11. LangGraph State

A shared typed state object shall maintain the execution context.

Example conceptual state:

```python
class SQLAgentState:
    question: str
    schema_context: str
    business_context: str
    generated_sql: str
    validation_errors: list[str]
    execution_error: str | None
    repair_attempts: int
    query_result: object | None
    final_answer: str | None
    execution_status: str
```

Pydantic models may be used for structured outputs exchanged between important nodes.

---

# 12. SQL Generation

The SQL-generation node shall receive:

```text
User Question
+
Relevant Schema
+
Business Definitions
+
SQL Dialect
+
Relevant Examples (future)
+
Generation Constraints
```

The model must be explicitly instructed to:

- Use only provided schema information.
- Never invent tables or columns.
- Generate only read-only SQL.
- Follow the target database dialect.
- Prefer efficient queries.
- Return structured output.

Example structured response:

```json
{
  "sql": "SELECT ...",
  "tables_used": ["orders", "customers"],
  "reasoning_summary": "Join orders with customers and aggregate revenue by region."
}
```

The system should not rely on unconstrained natural-language responses from the model.

---

# 13. SQL Validation

SQL shall pass several validation stages.

### Stage 1 — Syntax Validation

Check whether the SQL can be parsed.

A SQL parser such as **SQLGlot** can be introduced for dialect-aware SQL parsing and inspection.

### Stage 2 — Schema Validation

Verify:

```text
Table exists
Column exists
Join references are valid
Database/schema references are valid
```

### Stage 3 — Security Validation

Reject:

```text
INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
CREATE
GRANT
REVOKE
```

and other unauthorized operations.

### Stage 4 — Execution Validation

Execute the query using the read-only database connection.

### Stage 5 — Result Validation

Check whether the returned result is structurally and semantically reasonable.

---

# 14. Self-Healing Mechanism

The primary differentiating feature is automatic recovery from failed SQL.

Example:

Generated:

```sql
SELECT customer.name
FROM customer
JOIN orders
ON customer.id = orders.customer_id;
```

Database returns:

```text
relation "customer" does not exist
```

The error-diagnosis node receives:

```text
Original Question
Generated SQL
Database Error
Relevant Schema
```

and generates a corrected query:

```sql
SELECT customers.name
FROM customers
JOIN orders
ON customers.id = orders.customer_id;
```

The corrected SQL must **repeat the complete validation process** before being executed.

---

# 15. Retry Policy

Self-healing must be bounded.

Example:

```text
MAX_REPAIR_ATTEMPTS = 3
```

After the maximum number of failed attempts:

```text
Status: FAILED

Reason:
Unable to generate a valid query after 3 attempts.

Last database error:
...
```

The system must never enter an infinite repair loop.

---

# 16. Error Categories

Errors shall be classified into categories.

### Syntax Errors

```text
SQL parser errors
```

### Schema Errors

```text
Unknown table
Unknown column
Incorrect schema
```

### Join Errors

```text
Incorrect join
Missing join
Ambiguous join
```

### Semantic Errors

```text
Incorrect aggregation
Wrong business metric
Wrong date range
Wrong grouping
```

### Execution Errors

```text
Database timeout
Connection failure
Permission failure
Query failure
```

### Safety Errors

```text
Write operation
Destructive SQL
Unauthorized table
```

This classification will later support evaluation and model improvement.

---

# 17. SQL Safety

The system shall implement defense-in-depth.

### Layer 1

LLM prompt constraints.

### Layer 2

Structured model output.

### Layer 3

SQL parser/static validation.

### Layer 4

Application-level statement allowlist.

Preferred policy:

```text
ALLOW:
SELECT
WITH ... SELECT
```

Everything else is rejected unless explicitly approved.

### Layer 5

Dedicated read-only database credentials.

### Layer 6

Optional future database-level protections:

```text
statement_timeout
query cost limits
row limits
restricted schemas
network isolation
```

The database permission model remains the final security boundary.

---

# 18. Multi-Turn Conversations

Future V1/V2 functionality should allow:

```text
User:
Show revenue by region.

User:
Only for 2025.

User:
Now compare it with 2024.

User:
Show the top three regions.
```

The LangGraph state/checkpointing mechanism should preserve relevant conversational and analytical context.

---

# 19. API Requirements

FastAPI shall expose endpoints such as:

```text
POST /api/query
POST /api/query/stream
GET  /api/query/{query_id}
GET  /api/health
GET  /api/schema
```

Example:

```json
POST /api/query

{
  "question": "What were the top 5 products by revenue?"
}
```

Response:

```json
{
  "query_id": "...",
  "sql": "SELECT ...",
  "status": "success",
  "attempts": 1,
  "result": [...],
  "answer": "The top 5 products were ..."
}
```

---

# 20. Frontend Requirements

React.js interface shall provide:

### Query Interface

```text
Ask your database
[........................................]
             [Run Query]
```

### SQL View

Display generated SQL.

### Execution Status

```text
Schema Retrieved       ✓
SQL Generated          ✓
SQL Validated          ✓
Security Check         ✓
Executed               ✓
```

### Self-Healing View

When repair occurs:

```text
Attempt 1
✗ SQL execution failed

Error:
column "revenue" does not exist

Attempt 2
✓ Corrected SQL executed
```

### Result View

Provide:

- Table
- Basic visualization where appropriate
- Natural-language summary
- Generated SQL
- Execution metadata

---

# 21. Observability

Observability will be a major future enhancement.

The system should eventually instrument:

```text
API requests
LangGraph nodes
LLM calls
Schema retrieval
SQL validation
Database execution
Retries
Failures
Latency
Token usage
```

**OpenTelemetry** is a strong candidate for vendor-neutral instrumentation of traces, metrics, and future logging. Its Python SDK supports tracing and metrics, and applications can create custom spans around important operations.

Example trace:

```text
/query
│
├── query_understanding        120ms
├── schema_retrieval             80ms
├── llm_sql_generation         1.2s
├── sql_validation               30ms
├── database_execution          420ms
├── result_validation             60ms
└── response_generation         700ms
```

---

# 22. LangSmith Integration — Future Scope

**LangSmith** may be integrated as an LLM/agent observability and evaluation layer.

Potential capabilities:

```text
Trace LangGraph executions
Inspect prompts/responses
Compare model runs
Debug failed generations
Build evaluation datasets
Evaluate different prompts/models
Monitor latency and token usage
```

The architecture should therefore keep tracing/evaluation decoupled from the core business logic so that LangSmith can be added without redesigning the agent.

---

# 23. Evaluation Framework

A dedicated evaluation pipeline shall be developed.

For each test case:

```text
Question
Expected SQL / Expected Result
Generated SQL
Execution Result
Correct / Incorrect
Retries
Latency
Token Usage
Cost
Failure Type
```

### Primary metrics

**Execution Accuracy**

Whether the generated SQL produces the correct result.

**SQL Validity**

Percentage of generated SQL statements that execute successfully.

**Recovery Rate**

Percentage of initially failed queries successfully repaired.

**First-Attempt Accuracy**

Percentage of queries solved without repair.

**Average Repair Attempts**

Average number of self-healing iterations.

**Latency**

End-to-end response time.

**Cost**

Estimated LLM inference cost per query.

**Schema Retrieval Accuracy**

Whether relevant schema elements were retrieved.

---

# 24. Benchmarking

The project should eventually evaluate against public Text-to-SQL datasets such as:

```text
Spider
Spider 2.0 / Spider 2.0-Lite
BIRD
```

The evaluation architecture should make the benchmark dataset replaceable rather than hard-coded.

Additionally, a custom enterprise-style dataset should be created containing:

```text
Simple queries
JOIN queries
Aggregation queries
Nested queries
CTEs
Window functions
Ambiguous business questions
Incorrect-schema traps
Execution-error cases
Semantic-error cases
```

---

# 25. Model Strategy

V1 should use an external strong LLM rather than immediately fine-tuning a custom model.

The model interface shall be provider-independent:

```text
LLM Interface
      │
 ┌────┼───────────┐
 ↓    ↓           ↓
OpenAI  Open Model  Local Model
```

The application should be able to switch models through configuration rather than code changes.

Example:

```text
MODEL_PROVIDER
MODEL_NAME
TEMPERATURE
MAX_TOKENS
```

This allows future comparisons between:

```text
GPT
Claude
Gemini
DeepSeek
Kimi
GLM
Qwen
Other open-source models
```

without changing the LangGraph workflow.

---

# 26. Future Fine-Tuning

Fine-tuning will be considered only after establishing a strong baseline.

The objective will be:

> Determine whether a smaller specialized Text-to-SQL model can achieve competitive execution accuracy at substantially lower inference cost and latency.

Potential training data:

```text
Spider / appropriate licensed datasets
BIRD / appropriate licensed datasets
Synthetic enterprise queries
Internal schema-question-SQL pairs
Corrected SQL generated by the self-healing pipeline
Human-reviewed failure cases
```

Potential techniques:

```text
LoRA
QLoRA
PEFT
TRL
Unsloth
Hugging Face Transformers
```

The fine-tuned model can then become:

```text
Candidate Model
      ↓
Benchmark
      ↓
Compare against Strong API Model
      ↓
Accuracy / Cost / Latency
```

The goal is not simply to have a fine-tuned model, but to demonstrate a measurable improvement or cost-efficiency advantage.

---

# 27. Future MLOps Architecture

The long-term system can evolve into an ML/LLM evaluation platform.

```text
                 Production Queries
                        │
                        ▼
                  Trace + Log
                        │
                        ▼
                 Evaluation Store
                        │
            ┌───────────┴───────────┐
            ↓                       ↓
       Failure Analysis        Performance
            │                       │
            └───────────┬───────────┘
                        ↓
                   Dataset Builder
                        ↓
                  Model Experiment
                        ↓
                 Fine-Tuning / Prompt
                        ↓
                    Evaluation
                        ↓
                  Model Registry
                        ↓
                    Deployment
```

Potential future technologies:

```text
OpenTelemetry
LangSmith
MLflow
Prometheus
Grafana
Docker
Kubernetes
GitHub Actions
Model Registry
Vector Database
Feature / Dataset Versioning
```

OpenTelemetry is especially useful here because it supports vendor-neutral telemetry and can emit traces and metrics from both application code and instrumented dependencies.

---

# 28. Data Collection for Continuous Improvement

With appropriate privacy and security controls, failed production queries can become improvement data.

Example:

```text
Question
     ↓
Generated SQL
     ↓
Failure
     ↓
User/Agent Correction
     ↓
Validated SQL
     ↓
Human Review
     ↓
Evaluation Dataset
```

This dataset can later be used for:

```text
Prompt improvement
Few-shot retrieval
Schema-retrieval improvement
Fine-tuning
Regression testing
```

No sensitive production data should be incorporated into training datasets without explicit authorization and appropriate anonymization.

---

# 29. Security and Privacy Requirements

The system shall:

- Never expose database credentials to the LLM.
- Never allow the LLM to directly establish database connections.
- Use environment variables or secret management for credentials.
- Use dedicated read-only database credentials.
- Enforce SQL allowlisting outside the model.
- Apply query timeouts.
- Limit result size where appropriate.
- Avoid returning unnecessary sensitive columns.
- Log security failures.
- Support table/schema allowlists in future versions.
- Sanitize user-provided metadata before inserting it into prompts.

---

# 30. Reliability Requirements

The system shall:

- Have a bounded retry mechanism.
- Fail gracefully when SQL cannot be repaired.
- Never execute unvalidated SQL.
- Preserve intermediate agent state.
- Provide actionable error messages.
- Support configurable model timeouts.
- Support database connection pooling through SQLAlchemy.
- Return a clear failure state rather than hallucinating an answer.

---

# 31. Performance Requirements

Initial target:

```text
Simple query:
< 5 seconds

Complex query:
< 15 seconds
```

These are initial engineering targets and should be refined after benchmarking.

The system should track:

```text
LLM latency
Schema retrieval latency
SQL validation latency
Database execution latency
Total latency
```

---

# 32. Suggested Technology Stack

## Backend

```text
Python
FastAPI
LangChain
LangGraph
Pydantic
SQLAlchemy
SQLGlot
```

## Database

```text
PostgreSQL
pgvector (future)
```

## Frontend

```text
React.js
TypeScript
Tailwind CSS
```

## AI / LLM

```text
Configurable LLM provider
Open-source models
Hugging Face
PEFT / QLoRA (future)
```

## Infrastructure

```text
Docker
Redis (optional)
```

## Observability

```text
LangSmith (future)
OpenTelemetry
Prometheus / Grafana (future)
```

## MLOps

```text
MLflow (future)
GitHub Actions
Model/Dataset versioning
Evaluation pipelines
```

---

# 33. High-Level Repository Structure

```text
sqlpilot/
│
├── backend/
│   ├── api/
│   ├── agents/
│   │   ├── graph.py
│   │   ├── state.py
│   │   └── nodes/
│   ├── llm/
│   ├── sql/
│   │   ├── generator.py
│   │   ├── validator.py
│   │   ├── security.py
│   │   └── executor.py
│   ├── database/
│   │   ├── connection.py
│   │   └── schema.py
│   ├── evaluation/
│   └── observability/
│
├── frontend/
│
├── datasets/
│
├── experiments/
│
├── tests/
│
├── docker/
│
├── docs/
│
├── .env.example
├── docker-compose.yml
└── README.md
```

---

# 34. Development Phases

## Phase 1 — Baseline

Build:

```text
FastAPI
+
SQLAlchemy
+
PostgreSQL
+
LLM
```

Implement:

```text
Question → SQL → Read-only execution → Result
```

---

## Phase 2 — LangGraph Agent

Add:

```text
Schema retrieval
SQL generation
SQL validation
Execution
Retry loop
```

---

## Phase 3 — Self-Healing

Implement:

```text
Error classification
Error diagnosis
SQL repair
Bounded retries
Result validation
```

---

## Phase 4 — Security

Implement:

```text
Read-only DB role
SQL parser
Statement allowlist
Query limits
Timeouts
Table/schema restrictions
```

---

## Phase 5 — Evaluation

Add:

```text
Benchmark datasets
Execution accuracy
Recovery rate
Latency
Cost
Failure classification
```

---

## Phase 6 — Observability

Add:

```text
OpenTelemetry
LangSmith
Tracing
Metrics
LLM call logging
Agent-node tracing
```

OpenTelemetry can be introduced through Python SDK instrumentation and custom spans around LangGraph nodes, SQL execution, and LLM calls.

---

## Phase 7 — Model Experiments

Compare:

```text
Strong API model
Open-source models
Smaller models
Different prompts
Schema RAG vs no RAG
Self-healing vs no self-healing
```

---

## Phase 8 — Fine-Tuning

Create a curated dataset from:

```text
Benchmark data
Synthetic questions
Enterprise-style schema/question pairs
Validated failure-and-repair examples
```

Fine-tune a smaller model using:

```text
QLoRA / LoRA
```

Then compare it against the baseline using the same evaluation framework.

---

# 35. Success Criteria

The project will be considered successful when it can demonstrate:

```text
✓ Natural-language SQL generation
✓ Schema-grounded generation
✓ Read-only database enforcement
✓ SQL validation
✓ Automatic error detection
✓ Automatic SQL repair
✓ Bounded retry mechanism
✓ Correct execution results
✓ SQL + result transparency
✓ Evaluation metrics
✓ Model comparison
✓ Observable agent execution
```

A stronger final milestone is:

> Demonstrate that the self-healing pipeline substantially improves execution success compared with a single-pass Text-to-SQL baseline while maintaining acceptable latency and inference cost.

---

# 36. Long-Term Product Vision

The long-term vision is to evolve the system from a **Text-to-SQL chatbot** into an **enterprise AI data agent** capable of:

```text
Natural Language
       ↓
Intent Understanding
       ↓
Schema Intelligence
       ↓
Business Semantics
       ↓
SQL Planning
       ↓
SQL Generation
       ↓
Safety Validation
       ↓
Execution
       ↓
Self-Healing
       ↓
Result Validation
       ↓
Analytics / Visualization
```

Eventually, the system can become a complete **LLM-powered data-access layer** with model evaluation, observability, continuous dataset generation, fine-tuning, and model deployment capabilities.

---

# 37. Core Differentiator

The project's primary differentiator should be:

> **Reliability through self-healing rather than one-shot SQL generation.**

The project should demonstrate that an LLM does not need to produce perfect SQL on its first attempt; instead, the surrounding agent architecture should detect failures, understand why they occurred, repair the query, validate it, and safely retry.

That distinction makes the project substantially more meaningful as an **LLM/agent engineering project** than a basic "natural language to SQL" application.