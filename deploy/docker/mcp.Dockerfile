FROM python:3.12-slim

ADD https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz /tmp/uv.tar.gz
RUN tar -xzf /tmp/uv.tar.gz -C /tmp && mv /tmp/uv-x86_64-unknown-linux-gnu/uv /bin/uv && rm -rf /tmp/uv*

WORKDIR /app

COPY services/py/mcp/pyproject.toml .

RUN uv venv /app/.venv \
    && uv pip install --python /app/.venv \
        "mcp>=1.12" \
        "httpx>=0.28" \
        "pydantic-settings>=2.7"

ENV PATH="/app/.venv/bin:$PATH"

COPY services/py/mcp/ .

CMD ["python", "-m", "app.main"]
