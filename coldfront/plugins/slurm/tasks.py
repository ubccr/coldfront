from django.core.management import call_command

def slurm_sync():
    """ID and add new slurm allocations from ADGroup and ADUser data
    """
    call_command('slurm_sync')

def slurm_manage_resources():
    """ID and add new slurm allocations from ADGroup and ADUser data
    """
    call_command('slurm_manage_resources')
