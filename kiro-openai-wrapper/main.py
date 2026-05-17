"""kiro-cli OpenAI-Compatible API Wrapper.

Exposes kiro-cli as a standard OpenAI Chat Completions API.
Any OpenAI-compatible client can use this.

Usage:
    pip install fastapi uvicorn pydantic
    python -m uvicorn main:app --host 127.0.0.1 --port 8000

Then use:
    curl http://localhost:8000/v1/models
    curl -X POST http://localhost:8000/v1/chat/completions ...
"""

from fastapi import FastAPI
from api import router

app = FastAPI(title="kiro-cli OpenAI Wrapper")
app.include_router(router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs", "models": "/v1/models"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
