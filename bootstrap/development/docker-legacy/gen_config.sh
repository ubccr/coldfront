#!/usr/bin/env bash
cp coldfront/config/local_settings.py.sample coldfront/config/local_settings.py
cp coldfront/config/local_strings.py.sample coldfront/config/local_strings.py
python bootstrap/development/gen_config.py > coldfront/config/dev_settings.py
