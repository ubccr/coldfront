#!/bin/bash

DEPLOYMENT=$1
if [ "$DEPLOYMENT" != "BRC" ] && [ "$DEPLOYMENT" != "LRC" ]; then
    echo "Invalid deployment. Please specify either 'BRC' or 'LRC'."
    exit 1
fi

# Re-copy local settings and strings.
cp coldfront/config/local_settings.py.sample coldfront/config/local_settings.py
cp coldfront/config/local_strings.py.sample coldfront/config/local_strings.py

# Re-copy the base main.yml file.
cp bootstrap/ansible/main.copyme bootstrap/development/docker/config/main.yml

# Re-generate the Django development settings file.
(docker run -it \
    -v ./bootstrap/ansible/settings_template.tmpl:/tmp/settings_template.tmpl \
    -v ./bootstrap/development/docker:/app \
    coldfront-app-config:latest \
    python3 scripts/generate_django_settings_file.py $DEPLOYMENT) > coldfront/config/dev_settings.py
