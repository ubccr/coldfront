#!/bin/bash
#set -e

export DJANGO_SETTINGS_MODULE=coldfront.config.database


cd /opt/


if [[ "$INITIAL_SETUP" == "True" ]]; then
  #echo "yes\n" | coldfront initial_setup
  coldfront initial_setup
  python create_superuser.py
fi

if [[ "$LOAD_TEST_DATA" == "True" ]]; then
  echo "yes\n" | coldfront load_test_data
fi

# Avvia il server Django
echo "Avviando il server Django..."
if [[ "$DEBUG" == "True" ]]; then
  DEBUG=True python -m django runserver 0.0.0.0:8080
else
  python -m gunicorn coldfront.config.wsgi -b 0.0.0.0:8080 --capture-output
fi
