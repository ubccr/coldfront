from django.core.management import call_command

def xdmod_usage():
    """Add xdmod usage data
    """
    call_command('xdmod_usage', sync=True)
