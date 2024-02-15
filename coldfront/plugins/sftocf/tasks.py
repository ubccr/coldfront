from django.core import management

def pull_sf_push_cf():
    management.call_command('pull_sf_push_cf')
