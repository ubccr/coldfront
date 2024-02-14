import argparse
import os
import yaml

from jinja2 import Environment
from jinja2 import FileSystemLoader


SCRIPT_PATH = os.path.abspath(__file__)

DJANGO_SETTINGS_JINJA_TEMPLATE_DIRECTORY_PATH = '/tmp/'
DJANGO_SETTINGS_JINJA_TEMPLATE_FILE_NAME = 'settings_template.tmpl'

YAML_DIRECTORY_PATH = '/app/config/'
YAML_FILE_NAMES = [
    'main.yml',
    'docker_defaults.yml',
    'secrets.yml',
    'cilogon.yml',
]


def build_context(yaml_file_paths):
    context = {}
    for yaml_file_path in yaml_file_paths:
        with open(yaml_file_path, 'r') as f:
            yaml_dict = yaml.safe_load(f)
            context.update(yaml_dict)
    return context


def generate_settings(context):
    loader = FileSystemLoader(DJANGO_SETTINGS_JINJA_TEMPLATE_DIRECTORY_PATH)
    environment = Environment(loader=loader)
    environment.filters['bool'] = (
        lambda x: str(x).lower() in ['true', 'yes', 'on', '1'])
    template = environment.get_template(
        DJANGO_SETTINGS_JINJA_TEMPLATE_FILE_NAME)
    return template.render(context)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate default configuration for the application.')
    parser.add_argument(
        'deployment',
        choices=['BRC', 'LRC'],
        help='Specify the deployment to generate configuration for.')
    return parser.parse_args()


def main():
    args = parse_args()

    yaml_file_names = list(YAML_FILE_NAMES)

    deployment_yaml_file_name = f'{args.deployment.lower()}_defaults.yml'
    yaml_file_names.append(deployment_yaml_file_name)
    yaml_file_paths = [
        os.path.join(YAML_DIRECTORY_PATH, file_name)
        for file_name in yaml_file_names]

    context = build_context(yaml_file_paths)

    print(generate_settings(context))


if __name__ == '__main__':
    main()
