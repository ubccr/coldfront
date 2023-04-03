#!/usr/bin/env bash
cp coldfront/config/local_settings.py.sample \
    coldfront/config/local_settings.py
cp coldfront/config/local_strings.py.sample \
    coldfront/config/local_strings.py
python -c \
"from jinja2 import Template, Environment, FileSystemLoader; \
import yaml; \
env = Environment(loader=FileSystemLoader('bootstrap/ansible/')); \
env.filters['bool'] = lambda x: str(x).lower() in ['true', 'yes', 'on', '1']; \
options = yaml.safe_load(open('main.yml').read()); \
options.update({'redis_host': 'redis', 'db_host': 'db'}); \
print(env.get_template('settings_template.tmpl').render(options))" \
                                              > coldfront/config/dev_settings.py
