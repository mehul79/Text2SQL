import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

load_dotenv()

PGHOST = "localhost"
PGPORT = 5432
PGDB = os.getenv("POSTGRES_DB")

readonly_url = f"postgresql+psycopg2://readonly_user:devpass@{PGHOST}:{PGPORT}/{PGDB}"

readonly_engine = create_engine(readonly_url, pool_size=5)


def get_session():
    with Session(readonly_engine) as session:
        yield session


if __name__ == "__main__":
    with readonly_engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
        print("connection ok")
