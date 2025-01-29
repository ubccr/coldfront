from django.dispatch import receiver

from coldfront.core.allocation.signals import (
    allocation_user_attribute_edit,
    allocation_user_remove_on_slurm,
    allocation_user_add_on_slurm,
    allocation_raw_share_edit
)
from coldfront.plugins.slurm.utils import (
    slurm_update_raw_share,
    slurm_remove_assoc,
    slurm_add_assoc,
    slurm_update_account_raw_share
)


@receiver(allocation_user_attribute_edit)
def allocation_user_attribute_edit_handler(sender, **kwargs):
    slurm_update_raw_share(kwargs['user'], kwargs['account'], str(kwargs['raw_share']))


@receiver(allocation_user_remove_on_slurm)
def allocation_user_deactivate_handler(sender, **kwargs):
    slurm_remove_assoc(kwargs['username'], kwargs['account'])


@receiver(allocation_raw_share_edit)
def allocation_raw_share_edit_handler(sender, **kwargs):
    slurm_update_account_raw_share(kwargs['account'], str(kwargs['raw_share']))


@receiver(allocation_user_add_on_slurm)
def allocation_add_user_handler(sender, **kwargs):
    slurm_add_assoc(kwargs['username'], kwargs['cluster'], kwargs['account'])

