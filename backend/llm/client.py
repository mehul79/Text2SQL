import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

load_dotenv()


class SQLResponse(BaseModel):
    sql: str
    tables_used: list[str]
    reasoning: str


def get_llm():
    return ChatOpenAI(
        base_url=os.getenv("BASE_URL"),
        api_key=os.getenv("OPENCODE_API_KEY"),
        model=os.getenv("OPENROUTER_MODEL"),
        temperature=float(os.getenv("TEMPERATURE")),
    )


if __name__ == "__main__":
    structured_llm = get_llm().with_structured_output(SQLResponse)
    result = structured_llm.invoke(
        "Given a table 'customer' with column 'name', write SQL to list all names."
    )
    assert isinstance(result, SQLResponse)
    assert result.sql
    assert isinstance(result.tables_used, list)
    print(result)
