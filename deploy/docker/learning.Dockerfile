FROM python:3.12-slim

ADD https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz /tmp/uv.tar.gz
RUN tar -xzf /tmp/uv.tar.gz -C /tmp && mv /tmp/uv-x86_64-unknown-linux-gnu/uv /bin/uv && rm -rf /tmp/uv*

WORKDIR /app

COPY libs/py/common /libs/common

COPY services/py/learning/pyproject.toml .

RUN uv venv /app/.venv \
    && uv pip install --python /app/.venv /libs/common \
    && uv pip install --python /app/.venv \
        "fastapi>=0.115" \
        "uvicorn>=0.34" \
        "asyncpg>=0.30" \
        "pyjwt>=2.10" \
        "pydantic-settings>=2.7" \
        "prometheus-fastapi-instrumentator>=7.0" \
        "redis>=5.0" \
        "fsrs>=6.0"

ENV PATH="/app/.venv/bin:$PATH"

COPY services/py/learning/ .

EXPOSE 8007

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"]
