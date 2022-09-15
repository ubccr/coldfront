#!/bin/bash

# This script starts up all django processes that need to run upon startup.
# See https://docs.docker.com/config/containers/multi-service_container/ for more info.


# turn on bash's job control
# set -m

# RUN python3 ./manage.py initial_setup
# RUN python3 ./manage.py load_test_data
python ./manage.py qcluster &

python ./manage.py runserver 0.0.0.0:80 --insecure
