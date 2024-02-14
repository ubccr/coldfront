import os
import secrets
import yaml


SCRIPT_DIRECTORY_PATH = os.path.dirname(os.path.abspath(__file__))

SECRETS_DIRECTORY_PATH = os.path.normpath(
    os.path.join(SCRIPT_DIRECTORY_PATH, '..', 'secrets'))
DB_ADMIN_PASSWD_SECRET_FILE_NAME = 'db-postgres.postgres_password'
REDIS_PASSWD_SECRET_FILE_NAME = 'kv.redis_password'

CONFIG_DIRECTORY_PATH = os.path.normpath(
    os.path.join(SCRIPT_DIRECTORY_PATH, '..', 'config'))
REDIS_CONF_FILE_NAME = 'redis.conf'
SECRETS_YML_FILE_NAME = 'secrets.yml'


def generate_random_secret_key(length):
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(secrets.choice(chars) for i in range(length))


def user_confirmation():
    message = (
        'This will overwrite existing secrets. Do you wish to proceed? '
        '[Y/y/N/n]: ')
    user_input = input(message).strip().lower()
    return user_input == 'y'


def main():
    if not user_confirmation():
        return

    os.makedirs(SECRETS_DIRECTORY_PATH, exist_ok=True)

    django_secret_key = generate_random_secret_key(50)
    db_admin_passwd = generate_random_secret_key(20)
    redis_passwd = generate_random_secret_key(20)

    db_admin_passwd_secret_file_path = os.path.join(
        SECRETS_DIRECTORY_PATH, DB_ADMIN_PASSWD_SECRET_FILE_NAME)
    with open(db_admin_passwd_secret_file_path, 'w') as f:
        f.write(db_admin_passwd)

    redis_passwd_secret_file_path = os.path.join(
        SECRETS_DIRECTORY_PATH, REDIS_PASSWD_SECRET_FILE_NAME)
    with open(redis_passwd_secret_file_path, 'w') as f:
        f.write(redis_passwd)

    secrets_yml_file_path = os.path.join(
        CONFIG_DIRECTORY_PATH, SECRETS_YML_FILE_NAME)
    secrets_yml_data = {
        'django_secret_key': django_secret_key,
        'db_admin_passwd': db_admin_passwd,
        'redis_passwd': redis_passwd,
    }
    with open(secrets_yml_file_path, 'w') as f:
        yaml.dump(secrets_yml_data, stream=f)

    redis_conf_file_path = os.path.join(
        CONFIG_DIRECTORY_PATH, REDIS_CONF_FILE_NAME)
    redis_conf_contents = f'requirepass {redis_passwd}\n'
    with open(redis_conf_file_path, 'w') as f:
        f.write(redis_conf_contents)


if __name__ == '__main__':
    main()
