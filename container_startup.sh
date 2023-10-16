#!/bin/bash

# This script starts up all django processes that need to run upon startup.
# See https://docs.docker.com/config/containers/multi-service_container/ for more info.

# turn on bash's job control
# set -m

service redis-server start
python ./manage.py qcluster &
python ./manage.py add_scheduled_tasks
python ./manage.py collectstatic
# initial_setup does not appear to work as requested.
python ./manage.py initial_setup &

if [ "$BUILD_ENV" == 'dev' ]; then
    python ./manage.py runserver 0.0.0.0:80 --insecure
else
    gunicorn coldfront.config.wsgi:application --bind 0.0.0.0:80
fi
