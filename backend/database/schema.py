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


if __name__ == "__main__":
    tables = reflect_schema()
    assert "track" in tables
    assert any(c["name"] == "album_id" for c in tables["track"])
    print(f"reflected {len(tables)} tables")
