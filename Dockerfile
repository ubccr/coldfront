FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY . .

RUN uv sync --extra prod
RUN echo "yes" | uv run manage.py initial_setup
RUN uv run manage.py load_test_data

ENV DEBUG=True
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uv", "run", "manage.py", "runserver", "0.0.0.0:8000"]
