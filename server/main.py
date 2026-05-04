"""FastAPI server exposing TokenSqueeze.

Endpoints:
    POST /compress  — compress a prompt; returns text + stats + warnings.
    GET  /health    — liveness probe.
    GET  /stats     — cumulative session stats.

Default bind: 127.0.0.1:8765 (matches the browser extension default).
"""
from __future__ import annotations

import os
import time
from typing import Literal, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from tokensqueeze.compress import compress_detailed
from tokensqueeze.tokenizers import count_tokens


app = FastAPI(
    title="TokenSqueeze",
    version="0.1.0",
    description="Local prompt-compression service.",
)

# Browser extensions need CORS. Default to permissive; tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("TOKENSQUEEZE_CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CompressRequest(BaseModel):
    prompt: str = Field(..., description="The text to compress.")
    strategy: Literal["auto", "sns", "llmlingua2", "gist"] = "auto"
    encoding: str = Field("cl100k_base", description="tiktoken encoding for token counting.")
    explain: bool = Field(False, description="Include rule trace in the response.")


class TokenCounts(BaseModel):
    encoding: str
    original: int
    compressed: int
    saved: int
    reduction: float


class CompressResponse(BaseModel):
    original: str
    compressed: str
    strategy: str
    classified_as: Optional[str] = None
    warning: Optional[str] = None
    tokens: TokenCounts
    rules_applied: list[dict] = []


class StatsResponse(BaseModel):
    started_at: float
    requests: int
    total_original_tokens: int
    total_compressed_tokens: int
    total_saved_tokens: int
    average_reduction: float


_state = {
    "started_at": time.time(),
    "requests": 0,
    "total_original_tokens": 0,
    "total_compressed_tokens": 0,
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@app.post("/compress", response_model=CompressResponse)
def compress_endpoint(req: CompressRequest) -> CompressResponse:
    result = compress_detailed(req.prompt, strategy=req.strategy)
    o = count_tokens(req.prompt, req.encoding)
    c = count_tokens(result.compressed, req.encoding)
    saved = o - c
    reduction = (saved / o) if o else 0.0

    _state["requests"] += 1
    _state["total_original_tokens"] += o
    _state["total_compressed_tokens"] += c

    return CompressResponse(
        original=result.original,
        compressed=result.compressed,
        strategy=result.strategy,
        classified_as=result.classified_as,
        warning=result.warning,
        tokens=TokenCounts(
            encoding=req.encoding,
            original=o,
            compressed=c,
            saved=saved,
            reduction=round(reduction, 4),
        ),
        rules_applied=result.rules_applied if req.explain else [],
    )


@app.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    o = _state["total_original_tokens"]
    c = _state["total_compressed_tokens"]
    saved = o - c
    avg = (saved / o) if o else 0.0
    return StatsResponse(
        started_at=_state["started_at"],
        requests=_state["requests"],
        total_original_tokens=o,
        total_compressed_tokens=c,
        total_saved_tokens=saved,
        average_reduction=round(avg, 4),
    )


def run() -> None:  # pragma: no cover - manual run helper
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=os.environ.get("TOKENSQUEEZE_HOST", "127.0.0.1"),
        port=int(os.environ.get("TOKENSQUEEZE_PORT", "8765")),
        reload=False,
    )


if __name__ == "__main__":  # pragma: no cover
    run()
