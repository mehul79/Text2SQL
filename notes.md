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