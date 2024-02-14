#!/bin/bash

PROJECT_NAME=$1

docker-compose \
    -p $PROJECT_NAME \
    exec app-shell \
    /bin/bash -c "bootstrap/development/docker/scripts/run_django_scripts.sh"
