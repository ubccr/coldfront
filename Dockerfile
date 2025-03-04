FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY . .
RUN pip3 install setuptools
RUN pip3 install debugpy
RUN pip3 install python-dateutil
RUN pip3 install .[all]

RUN echo "yes" | python3 ./manage.py initial_setup
RUN python3 ./manage.py load_test_data

ENV DEBUG=True
ENV DJANGO_DEBUG=True
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
