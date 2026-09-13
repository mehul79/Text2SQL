from sqlalchemy import MetaData

from backend.database.connection import readonly_engine


def reflect_schema():
    metadata = MetaData()
    metadata.reflect(bind=readonly_engine)

    tables = {}
    for table_name, table in metadata.tables.items():
        columns = []
        for col in table.columns:
            fk = list(col.foreign_keys)
            columns.append({
                "name": col.name,
                "type": str(col.type),
                "foreign_key": fk[0].target_fullname if fk else None,
            })
        tables[table_name] = columns
    return tables


def format_schema(tables: dict) -> str:
    lines = []
    for table_name, columns in tables.items():
        col_descriptions = ", ".join(
            f"{c['name']} {c['type']}" + (f" -> {c['foreign_key']}" if c["foreign_key"] else "")
            for c in columns
        )
        lines.append(f"{table_name}({col_descriptions})")
    return "\n".join(lines)


if __name__ == "__main__":
    tables = reflect_schema()
    assert "track" in tables
    assert any(c["name"] == "album_id" for c in tables["track"])
    print(f"reflected {len(tables)} tables")
