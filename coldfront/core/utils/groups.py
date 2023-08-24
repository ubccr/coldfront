from django.contrib.auth.models import Permission

def check_if_groups_in_review_groups(review_groups, groups, permission=None):
    """
    Returns True if at least one group in a group query is included in a review group query. An
    additional permission can be given to check if at least one matching group has it. Since this
    is for determining permissions this returns True if the review group query is empty, meaning
    open to all groups. A user must be in at least one group or this will always return False.

    :param review_groups: The review group query to compare the groups to
    :param groups: The group query being compared
    :param permission: A permission at least one matching group should have
    """
    if not groups.exists():
        return False

    if not review_groups.exists():
        return True

    # Intersection is not supported on the database backend we use (MySql)
    matched_groups = [group for group in groups if group in review_groups]
    if matched_groups:
        if permission is None:
            return True

        matched_group_ids = [group.id for group in matched_groups]
        permission_exists = Permission.objects.filter(
            group__id__in=matched_group_ids, codename=permission
        ).exists()
        if permission_exists:
            return True

    return False
