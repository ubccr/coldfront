FROM registry.access.redhat.com/ubi10/python-312-minimal
USER 1001

LABEL name="coldfront" \
      vendor="NYU RTS" \
      description="For production use to deploy Coldfront in RTC" 

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
RUN chown -R 1001:0 /app && \
    chmod -R g=u /app

# From uv template: Install the project's dependencies using the lockfile and settings
# Need to relabel due to SELinux restrictions, ref: https://github.com/containers/podman/issues/26020
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock,relabel=shared \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,relabel=shared \
    uv sync --locked --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --extra prod --no-dev

# Run initial setup process
RUN echo "yes" | uv run manage.py initial_setup

# Default port for gunicorn
EXPOSE 8000

# Remove when we get users, but keep it for testing for now
ENV DEBUG=True
ENV PYTHONUNBUFFERED=1
EXPOSE 5678
