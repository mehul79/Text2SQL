## Create a read-only role in Postgres

```sql
CREATE ROLE readonly_user WITH LOGIN PASSWORD 'devpass';

GRANT CONNECT ON DATABASE text2sql TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;
```

## Sqlalchemy commands

```
conn.execute(customers.insert(), [])
conn.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user"))

```

## __name__ == __main__

- this is used to keep the same file to be run and tested on its own as well as to be able to import it
- when we run a file directly python sets the "__name__" = "__main__" and we have a check in the file that if name == main then do a specific task
- it a file is imported as a module that the imported files's main won't ever run providing guardrail

## __init__.py

- used to make a folder into a package which is easily importable 
- e.g. → `from backend.database.connection import get_session`

## Misc

- what middleware next would do in express the same thing is the `Depends` use eg - `def schema(session: Session = Depends(get_session)):`
