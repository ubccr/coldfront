from jinja2 import Environment
from jinja2 import FileSystemLoader
import yaml


env = Environment(loader=FileSystemLoader('bootstrap/ansible/'))
env.filters['bool'] = lambda x: str(x).lower() in ['true', 'yes', 'on', '1']
options = yaml.safe_load(open('main.yml').read())
options.update({
    'db_host': 'db',
    'email_host': 'email',
    'redis_host': 'redis',
})
print(env.get_template('settings_template.tmpl').render(options))
