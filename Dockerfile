ARG working_location=/app/

ARG python_version=3.12
ARG uv_version=0.7

ARG uv_image=ghcr.io/astral-sh/uv:${uv_version}-python${python_version}-bookworm-slim
ARG base_image=python:${python_version}-slim-bookworm

ARG expose_port=8000


# See https://docs.astral.sh/uv/guides/integration/docker/ which was used as a reference for this Dockerfile


######## Builder Image ########

FROM ${uv_image} AS builder

# Get all the dependencies needed to build the application
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
        libpq-dev \
        libkrb5-dev \
        libldap2-dev \
        libsasl2-dev \
        python3-dev \
        pkg-config \
        default-libmysqlclient-dev \
        cmake \
        libdbus-1-dev \
        freeipa-client \
        libglib2.0-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# consume ARGs so they are available in this stage
ARG working_location

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

ENV UV_PYTHON_DOWNLOADS=0

WORKDIR ${working_location}

COPY . .

RUN uv sync \
        --locked \
        --no-dev \
        --no-editable \
        --compile-bytecode \
        --extra ldap \ 
        --extra freeipa \
        --extra iquota \
        --extra oidc \
        --extra mysql \
        --extra pg 
        


######## Production Image ########

FROM ${base_image} AS production

# consume ARGs so they are available in this stage
ARG working_location
ARG expose_port

# Get sqlite
RUN apt-get update && apt-get install -y --no-install-recommends \
        sqlite3 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
 
WORKDIR ${working_location}

COPY --from=builder ${working_location} ${working_location}

ENV PATH=${working_location}/.venv/bin:$PATH

EXPOSE ${expose_port}
