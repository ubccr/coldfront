#!/bin/bash

python3 manage.py initial_setup
python3 manage.py add_accounting_defaults
python3 manage.py create_allocation_periods
python3 manage.py add_allowance_defaults
python3 manage.py add_directory_defaults
python3 manage.py create_staff_group
python3 manage.py collectstatic --noinput
