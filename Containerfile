FROM registry.cloud.rt.nyu.edu/nyu-rts/ubi/ubi9

# Build Python as superuser!
RUN dnf install -y python3.12 && dnf update -y

LABEL name="coldfront" \
      vendor="NYU RTS" \
      description="For production use to deploy Coldfront in RTC" 

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Need this to prevent os13 errors on shipwright.
ENV UV_CACHE_DIR=/tmp

# From uv template: Install the project's dependencies using the lockfile and settings
# Need to relabel due to SELinux restrictions, ref: https://github.com/containers/podman/issues/26020
RUN --mount=type=bind,source=uv.lock,target=uv.lock,relabel=shared \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,relabel=shared \
    uv sync --locked --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --extra prod --no-dev

# Default port for gunicorn
EXPOSE 8000

# Remove when we get users, but keep it for testing for now
ENV DEBUG=True
ENV PYTHONUNBUFFERED=1
EXPOSE 5678
