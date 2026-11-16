FROM ghcr.io/astral-sh/uv:0.9.28 AS uv
FROM python:3.11-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 course
WORKDIR /app
ENV UV_LINK_MODE=copy PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    DEEPEVAL_TELEMETRY_OPT_OUT=YES RAGAS_DO_NOT_TRACK=true \
    PATH="/app/.venv/bin:$PATH" KNOWLEDGE_DIR=/data/knowledge RUNS_DIR=/data/runs
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project
COPY --chown=course:course . .
RUN mkdir -p /data/knowledge /data/runs \
    && chown course:course /app /data /data/knowledge /data/runs
USER course
EXPOSE 8000
ENTRYPOINT ["python", "-m", "eval_course"]
CMD ["serve"]
