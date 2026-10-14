FROM apache/superset:6.0.0
USER root
RUN uv pip install --python /app/.venv/bin/python psycopg2-binary==2.9.10
USER superset
