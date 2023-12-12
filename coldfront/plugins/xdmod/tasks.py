from django.core.management import call_command

def xdmod_usage():
    """ID and add new slurm allocations from ADGroup and ADUser data
    """
    call_command('slurm_sync', sync=True)
