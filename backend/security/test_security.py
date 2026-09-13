from backend.security.sql_guard import validate_sql


def test_plain_select_passes():
    assert validate_sql("SELECT id, name FROM customer") == []


def test_cte_select_passes():
    assert validate_sql("WITH x AS (SELECT * FROM customer) SELECT * FROM x") == []


def test_stacked_statements_rejected():
    assert validate_sql("SELECT 1; DROP TABLE customer;") != []


def test_delete_hidden_in_cte_rejected():
    sql = "WITH deleted AS (DELETE FROM customer WHERE id = 1 RETURNING *) SELECT * FROM deleted"
    assert validate_sql(sql) != []


def test_update_dressed_as_subquery_rejected():
    sql = "SELECT * FROM (UPDATE customer SET name = 'x' WHERE id = 1 RETURNING *) t"
    assert validate_sql(sql) != []


def test_comment_smuggled_drop_is_inert():
    # the drop is text inside a comment, not a second statement — parser sees only the SELECT
    sql = "SELECT * FROM customer /* ; DROP TABLE customer; */"
    assert validate_sql(sql) == []


def test_ddl_rejected():
    for stmt in [
        "INSERT INTO customer (name) VALUES ('x')",
        "UPDATE customer SET name = 'x'",
        "DROP TABLE customer",
        "ALTER TABLE customer ADD COLUMN x int",
        "TRUNCATE customer",
        "CREATE TABLE x (id int)",
    ]:
        assert validate_sql(stmt) != [], f"expected rejection for: {stmt}"


def test_unknown_table_rejected():
    assert validate_sql("SELECT * FROM ghost_table", known_tables={"customer"}) != []


def test_known_table_passes():
    assert validate_sql("SELECT * FROM customer", known_tables={"customer"}) == []


def test_syntax_error_rejected():
    assert validate_sql("SELEKT * FORM customer") != []


COLUMNS = {"customer": {"customer_id", "first_name", "last_name"}}


def test_known_column_passes():
    assert validate_sql("SELECT first_name FROM customer", known_columns=COLUMNS) == []


def test_known_qualified_column_passes():
    assert validate_sql("SELECT c.first_name FROM customer c", known_columns=COLUMNS) == []


def test_unknown_column_rejected():
    assert validate_sql("SELECT ssn FROM customer", known_columns=COLUMNS) != []


def test_unknown_qualified_column_rejected():
    assert validate_sql("SELECT c.ssn FROM customer c", known_columns=COLUMNS) != []


def test_select_alias_referenced_in_order_by_passes():
    sql = "SELECT COUNT(*) AS n FROM customer ORDER BY n"
    assert validate_sql(sql, known_columns=COLUMNS) == []


def test_cte_column_check_skipped_not_rejected():
    # a CTE's own columns aren't in known_columns — the check must not misfire on them
    sql = "WITH recent AS (SELECT first_name FROM customer) SELECT first_name FROM recent"
    assert validate_sql(sql, known_columns=COLUMNS) == []


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"{len(tests)} security tests passed")
