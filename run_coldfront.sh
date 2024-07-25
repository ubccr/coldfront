#!/bin/bash

set -xe

>&2 echo "Waiting for database..."

export DJANGO_SETTINGS_MODULE=coldfront.config.database

DATABASE_PORT=${DATABASE_PORT:-3306}

while ! echo exit | nc $DATABASE_HOST $DATABASE_PORT; do sleep 5; done

>&2 echo "Database is up - Starting"

sleep 10

if [[ "$INITIAL_SETUP" == "True" ]]
then
  python -m django initial_setup
  python -m django register_cloud_attributes
fi

if [[ "$LOAD_TEST_DATA" == "True" ]]
then
  python -m django load_test_data
fi

if [[ "$DEBUG" == "True" ]]
then
  python -m django runserver 0.0.0.0:8080
else
  python -m gunicorn coldfront.config.wsgi -b 0.0.0.0:8080 --capture-output
fi