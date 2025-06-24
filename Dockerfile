FROM python:3.12

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
RUN pip3 install --upgrade pip uv "setuptools<81"
COPY . .
RUN uv venv .venv
RUN . .venv/bin/activate \
    && uv pip install .
RUN . .venv/bin/activate \
    && python3 ./manage.py initial_setup -f
RUN . .venv/bin/activate \
    && python3 ./manage.py load_test_data

ENV DEBUG=True

EXPOSE 8000
CMD ["bash", "-c", ". .venv/bin/activate && python3 ./manage.py runserver 0.0.0.0:8000"]
