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
    
    session_id = os.getenv("LLM_SESSION_ID")

    return ChatOpenAI(
        base_url=os.environ["BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        model=os.environ["MODEL_NAME"],
        temperature=float(os.getenv("TEMPERATURE", 0)),
        default_headers={"x-opencode-session": session_id} if session_id else None,
    )


def get_structured_llm():
    # method="function_calling" is load-bearing: this provider ignores response_format
    # json_schema and answers in prose, which then fails Pydantic parsing. Tool calling
    # it does honour. Every caller must go through here.
    return get_llm().with_structured_output(SQLResponse, method="function_calling")


if __name__ == "__main__":
    structured_llm = get_structured_llm()
    result = structured_llm.invoke(
        "Given a table 'customer' with column 'name', write SQL to list all names."
    )
    assert isinstance(result, SQLResponse)
    assert result.sql
    assert isinstance(result.tables_used, list)
    print(result)
