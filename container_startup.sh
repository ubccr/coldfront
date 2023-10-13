#!/bin/bash

# This script starts up all django processes that need to run upon startup.
# See https://docs.docker.com/config/containers/multi-service_container/ for more info.


# turn on bash's job control
# set -m

service redis-server start
python ./manage.py qcluster &
python ./manage.py add_scheduled_tasks
python ./manage.py collectstatic --no-input

gunicorn coldfront.config.wsgi:application --bind 0.0.0.0:80
