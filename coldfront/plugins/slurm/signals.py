from django.dispatch import receiver

from coldfront.core.allocation.models import AllocationUser, AllocationUserAttributeType
from coldfront.core.allocation.signals import (
    allocation_user_attribute_edit,
    allocation_user_remove_on_slurm,
    allocation_user_add_on_slurm,
    allocation_activate_user,
    allocation_raw_share_edit
)
from coldfront.plugins.slurm.utils import (
    slurm_update_raw_share,
    slurm_remove_assoc,
    slurm_add_assoc,
    slurm_get_user_info,
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
    slurm_add_assoc(kwargs['username'], kwargs['cluster'], kwargs['account'], specs=['Fairshare=parent'])

@receiver(allocation_activate_user)
def allocation_activate_user_handler(sender, **kwargs):
    """import slurm data about user to coldfront when user is activated"""
    allocationuser = AllocationUser.objects.get(pk=kwargs['allocation_user_pk'])
    username = allocationuser.user.username
    project_title = allocationuser.allocation.project.title
    slurm_stats = slurm_get_user_info(username, project_title)
    keys = slurm_stats[0].split('|')
    values = next(i for i in slurm_stats if username in i and project_title in i).split('|')
    stats = dict(zip(keys, values))
    # Extract only the fields we want in the order specified
    wanted_fields = ['RawShares', 'NormShares', 'RawUsage', 'FairShare']
    result = ','.join(f"{field}={stats[field]}" for field in wanted_fields)
    # set the value of the allocationuser attribute to the result
    slurm_specs_allocuser_attrtype = AllocationUserAttributeType.objects.get(name='slurm_specs')
    allocationuser.allocationuserattribute_set.update_or_create(
        allocationuser_attribute_type=slurm_specs_allocuser_attrtype,
        defaults={"value": result}
    )

