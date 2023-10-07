#!/bin/bash

# This script starts up all django processes that need to run upon startup.
# See https://docs.docker.com/config/containers/multi-service_container/ for more info.


# turn on bash's job control
# set -m

service redis-server start
python ./manage.py qcluster &
python ./manage.py add_scheduled_tasks
source /srv/coldfront/venv/bin/activate
python ./manage.py collectstatic
# initial_setup does not appear to work as requested.
python ./manage.py initial_setup &

case $1 in
    'dev')
            python ./manage.py runserver 0.0.0.0:80 --insecure
        ;;
    *)
            python ./manage.py runserver 0.0.0.0:80
        ;;
esac
