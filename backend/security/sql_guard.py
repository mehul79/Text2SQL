import sqlglot
from sqlglot import exp

# ponytail: allowlist checked via AST node types, not a keyword blocklist —
# a string can't hide a DROP/DELETE from the parser the way it can from regex.
FORBIDDEN_EXPR = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Grant,
    exp.TruncateTable,
)


def validate_sql(
    sql: str,
    known_tables: set[str] | None = None,
    known_columns: dict[str, set[str]] | None = None,
) -> list[str]:
    """Return a list of validation errors; empty list means the SQL is safe to run.

    known_columns maps lowercase table name -> set of lowercase column names.
    """
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except Exception as e:
        return [f"syntax error: {e}"]

    if len(statements) != 1:
        return ["only a single SQL statement is allowed"]

    stmt = statements[0]
    errors = []

    if not isinstance(stmt, (exp.Select, exp.With)):
        errors.append(f"only SELECT / WITH...SELECT statements are allowed, got {type(stmt).__name__}")

    for forbidden in FORBIDDEN_EXPR:
        if stmt.find(forbidden):
            errors.append(f"disallowed operation: {forbidden.__name__}")

    # CTE names (WITH x AS (...)) are queried like tables but aren't real ones —
    # exclude them from both checks rather than flag them as unknown.
    cte_names = {cte.alias_or_name.lower() for cte in stmt.find_all(exp.CTE)}

    if known_tables is not None:
        for table in stmt.find_all(exp.Table):
            name = table.name.lower()
            if name not in cte_names and name not in known_tables:
                errors.append(f"unknown table: {table.name}")

    if known_columns is not None:
        alias_to_table = {
            t.alias_or_name.lower(): t.name.lower()
            for t in stmt.find_all(exp.Table)
            if t.name.lower() not in cte_names
        }
        real_tables = [t for t in alias_to_table.values() if t in known_columns]

        # SELECT ... AS x lets ORDER BY / GROUP BY reference x unqualified —
        # those aren't real columns, so they'd otherwise false-positive here.
        select_aliases = {a.alias.lower() for a in stmt.find_all(exp.Alias) if a.alias}

        for column in stmt.find_all(exp.Column):
            col_name = column.name.lower()
            qualifier = (column.table or "").lower()

            if qualifier:
                table = alias_to_table.get(qualifier, qualifier)
                if table in cte_names:
                    continue  # can't check columns of a CTE without resolving its body
                if table in known_columns and col_name not in known_columns[table]:
                    errors.append(f"unknown column: {column.table}.{column.name}")
            elif (
                real_tables
                and col_name not in select_aliases
                and not any(col_name in known_columns[t] for t in real_tables)
            ):
                errors.append(f"unknown column: {column.name}")

    return errors


if __name__ == "__main__":
    COLUMNS = {"customer": {"customer_id", "first_name", "last_name"}, "track": {"track_id", "name"}}

    assert validate_sql("SELECT * FROM customer") == []
    assert validate_sql("DELETE FROM customer") != []
    assert validate_sql("SELECT * FROM customer; DROP TABLE customer;") != []
    assert validate_sql("SELECT * FROM ghost_table", known_tables={"customer"}) != []

    assert validate_sql("SELECT first_name FROM customer", known_columns=COLUMNS) == []
    assert validate_sql("SELECT c.first_name FROM customer c", known_columns=COLUMNS) == []
    assert validate_sql("SELECT ghost_column FROM customer", known_columns=COLUMNS) != []
    assert validate_sql("SELECT c.ghost_column FROM customer c", known_columns=COLUMNS) != []
    # a name valid on a different table, unqualified, is still a real gap in this check —
    # it can't tell which table an unqualified column belongs to without more work
    assert validate_sql(
        "WITH x AS (SELECT * FROM customer) SELECT * FROM x", known_tables={"customer"}
    ) == []
    # ORDER BY / GROUP BY can reference a SELECT-list alias unqualified — not a real column
    assert validate_sql(
        "SELECT COUNT(*) AS n FROM customer ORDER BY n", known_columns=COLUMNS
    ) == []
    print("sql_guard self-check passed")
