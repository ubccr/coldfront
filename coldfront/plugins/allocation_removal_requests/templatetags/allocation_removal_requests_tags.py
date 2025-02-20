from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

from coldfront.core.utils.groups import check_if_groups_in_review_groups

register = template.Library()


# settings value
@register.simple_tag
def has_admin_perm(allocation_obj, user, addtl_perm=None):
    if user.is_superuser:
        return True

    group_exists = check_if_groups_in_review_groups(
        allocation_obj.get_parent_resource.review_groups.all(),
        user.groups.all(),
        addtl_perm,
    )
    return group_exists
