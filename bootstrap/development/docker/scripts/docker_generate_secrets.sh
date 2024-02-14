#!/bin/bash

docker run -it \
    -v ./bootstrap/development/docker:/app \
    coldfront-app-config:latest \
    python3 scripts/generate_secrets.py
