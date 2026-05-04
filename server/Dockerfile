FROM python:3.11-slim

WORKDIR /app

# Install only what we need; LLMLingua / sentence-transformers are optional.
COPY pyproject.toml README.md ./
COPY tokensqueeze ./tokensqueeze
COPY server ./server

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir ".[server]"

ENV TOKENSQUEEZE_HOST=0.0.0.0
ENV TOKENSQUEEZE_PORT=8765
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/health').status==200 else 1)"

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8765"]
