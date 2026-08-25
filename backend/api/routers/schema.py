from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import MetaData
from sqlalchemy.orm import Session

from backend.database.connection import get_session

router = APIRouter()


class Column(BaseModel):
    name: str
    type: str
    foreign_key: str | None = None


class SchemaResponse(BaseModel):
    tables: dict[str, list[Column]]


@router.get("/api/health")
def health():
    return {"status": "ok"}


@router.get("/api/schema", response_model=SchemaResponse)
def schema(session: Session = Depends(get_session)):
    metadata = MetaData()
    metadata.reflect(bind=session.get_bind())

    tables = {}
    for table_name, table in metadata.tables.items():
        columns = []
        for col in table.columns:
            fk = list(col.foreign_keys)
            columns.append(Column(
                name=col.name,
                type=str(col.type),
                foreign_key=fk[0].target_fullname if fk else None,
            ))
        tables[table_name] = columns
    return SchemaResponse(tables=tables)
