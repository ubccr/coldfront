#!/bin/bash
#set -e

>&2 echo "Waiting for database..."
DATABASE_PORT=${DATABASE_PORT:-3306}
while ! echo exit | nc $DATABASE_HOST $DATABASE_PORT; do sleep 5; done
>&2 echo "Database is up - Starting"
sleep 10


if [[ "$INITIAL_SETUP" == "True" ]]; then
  echo "yes" | coldfront initial_setup
  python create_superuser.py
fi

if [[ "$LOAD_TEST_DATA" == "True" ]]; then
  echo "yes" | coldfront load_test_data
fi

coldfront migrate

# Avvia il server Django
echo "Avviando il server Django..."
if [[ "$DEBUG" == "True" ]]; then
  echo "Starting debug server"
  coldfront runserver 0.0.0.0:8000
else
  echo "Starting prod gunicorn server"
  echo "yes" | python manage.py collectstatic
  python -m gunicorn coldfront.config.wsgi -b 0.0.0.0:8000 --capture-output
fi

