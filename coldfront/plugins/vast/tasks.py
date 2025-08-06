from django.core.management import call_command

def pull_vast_quotas():
    """Pull VAST quotas and update the database."""
    call_command('pull_vast_quotas')
