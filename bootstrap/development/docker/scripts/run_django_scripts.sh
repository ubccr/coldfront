#!/bin/bash

python manage.py initial_setup
python manage.py add_accounting_defaults
python manage.py create_allocation_periods
python manage.py add_allowance_defaults
python manage.py add_directory_defaults
python manage.py create_staff_group
python manage.py collectstatic --noinput
