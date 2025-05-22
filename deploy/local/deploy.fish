#!/usr/bin/env fish

# Run this from the project root directory
uv run manage.py collectstatic --noinput
podman build --tag "coldfront:debugpy" -f Containerfile.debugpy
podman pod create --name=django-caddy-gunicorn -p 8888:80 -p 5678:5678
podman run -d -v (pwd)/deploy/local/Caddyfile:/etc/caddy/Caddyfile -v (pwd)/static_root:/srv/static --pod=django-caddy-gunicorn caddy:alpine
podman run -d --pod=django-caddy-gunicorn coldfront:debugpy
