from fastapi import FastAPI

from backend.api.routers import models, query, schema

app = FastAPI()

app.include_router(schema.router)
app.include_router(models.router)
app.include_router(query.router)


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
