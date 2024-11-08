import logging
from django.utils import timezone
from coldfront.core.allocation.models import AllocationUserStatusChoice

logger = logging.getLogger(__name__)

class AllocationQueryMatch:
    """class to hold Allocations and related query results together."""
    def __new__(cls, allocation, total_usage_entries, user_usage_entries):
        allocation_data = (
            allocation.pk, allocation.project.title, allocation.resources.first()
        )
        msg = None
        if not total_usage_entries:
            msg = f'No starfish allocation usage result for allocation {allocation_data}; deactivation suggested'
        elif len(total_usage_entries) > 1:
            msg = f'too many total_usage_entries for allocation {allocation_data}; investigation required'
        if msg:
            print(msg)
            logger.warning(msg)
            return None
        return super().__new__(cls)

    def __init__(self, allocation, total_usage_entries, user_usage_entries):
        self.allocation = allocation
        self.volume = allocation.get_parent_resource.name.split('/')[0]
        self.path = allocation.path
        self.total_usage_entry = total_usage_entries[0]
        self.user_usage_entries = user_usage_entries

    @property
    def lab(self):
        return self.allocation.project.title

    @property
    def total_usage_tb(self):
        return round((self.total_usage_entry['total_size']/1099511627776), 5)

    @property
    def query_usernames(self):
        return [u['username'] for u in self.user_usage_entries]

    def update_user_usage(self, user, usage_bytes, usage, unit):
        """Get or create an allocationuser object with updated usage values."""
        allocationuser, created = self.allocation.allocationuser_set.get_or_create(
            user=user,
            defaults={
                'created': timezone.now(),
                'status': AllocationUserStatusChoice.objects.get(name='Active')
            }
        )
        if created:
            logger.info('allocation user %s created', allocationuser)
        allocationuser.usage_bytes = usage_bytes
        allocationuser.usage = usage
        allocationuser.unit = unit
        allocationuser.save()
        return allocationuser

    def update_usage_attr(self, usage_attribute_type, usage_value):
        usage_attribute, _ = self.allocation.allocationattribute_set.get_or_create(
            allocation_attribute_type=usage_attribute_type
        )
        usage = usage_attribute.allocationattributeusage
        usage.value = usage_value
        usage.save()
        return usage

    def users_in_list(self, username_list):
        """return usage entries for users with usernames in the provided list"""
        return [u for u in self.user_usage_entries if u['username'] in username_list]

    def users_not_in_list(self, username_list):
        """return usage entries for users with usernames not in the provided list"""
        return [u for u in self.user_usage_entries if u['user_name'] not in username_list]

