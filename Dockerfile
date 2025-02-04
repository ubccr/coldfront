ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1
ENV PYTHONUNBUFFERED 1
ARG BASE_IMAGE=python:3.12.8-alpine3.21

FROM $BASE_IMAGE AS base


###########
# BUILDER #
###########

# Pull official base image
FROM base AS builder

## Install build dependencies
# cache type mounts to only download changes in packages or versions on each build
RUN --mount=type=cache,target=/var/cache/apk apk update
RUN --mount=type=cache,target=/var/cache/apk apk add \
  git \
  build-base \
  meson \
  openldap-dev \
  python3-dev \
  sqlite


# This approximately follows this guide: https://hynek.me/articles/docker-uv/
# Which creates a standalone environment with the dependencies.
# - Silence uv complaining about not being able to use hard links,
# - tell uv to byte-compile packages for faster application startups,
# - prevent uv from accidentally downloading isolated Python builds,
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /bin/uv

WORKDIR /app
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies in a separate layer since these are relatively frozen in time
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync \
  --frozen \
  --no-install-project \
  --extra auth \
  --extra prod

COPY coldfront ./coldfront
COPY AUTHORS.md .
COPY CHANGELOG.md .
COPY MANIFEST.in .
COPY LICENSE .
COPY README.md .
COPY manage.py .
# Install our project
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync \
  --frozen \
  --extra prod

# Alternative using pip with setup.py
#RUN --mount=type=cache,target=/root/.cache/uv \
#  uv pip install \
#  --python=$UV_PROJECT_ENVIRONMENT \
#  --no-deps \
#  /app

###################################################################
# FINAL #
#########

# Pull official base image
FROM base AS production

# Install base dependencies
RUN --mount=type=cache,target=/var/cache/apk apk update
RUN --mount=type=cache,target=/var/cache/apk apk add \
  sqlite

# Unprivileged user
ARG user=app
ARG group=app
ARG uid=1000
ARG gid=1000
RUN addgroup -S -g ${gid} ${group}
RUN adduser -H -D -S -G ${group} -u ${uid} ${user}

COPY --from=builder --chown=${user}:${group} /app /app
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app

RUN mkdir /etc/coldfront
RUN mkdir /static
RUN mkdir /mediafiles
# sqlite db needs to be in ${user} writable directory
RUN touch coldfront.db
#COPY ./entrypoint.sh /
RUN chown ${user}:${group} /etc/coldfront /static /mediafiles /app coldfront.db
RUN chmod 750 /etc/coldfront /static /mediafiles /app
RUN chmod 640 coldfront.db

USER ${uid}:${gid}

# Strictly optional, but I like it for introspection of what I've built
# and run a smoke test that the application can, in fact, be imported.
RUN <<EOT
python -V
python -Im site
python -Ic 'import coldfront'
EOT

#ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8000", "coldfront.config.wsgi"]
