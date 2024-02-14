#!/bin/bash

PROJECT_NAME=$1
RELATIVE_CONTAINER_DUMP_FILE_PATH=$2

# TODO: There may be other services in the future.
docker-compose -p $PROJECT_NAME stop web

docker-compose \
    -p $PROJECT_NAME \
    exec db-postgres-shell \
    /bin/bash -c "bootstrap/development/docker/scripts/load_database_backup.sh $RELATIVE_CONTAINER_DUMP_FILE_PATH"

docker-compose -p $PROJECT_NAME start web
