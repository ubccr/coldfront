from typing import Optional
from django.contrib.auth.models import User

from coldfront.plugins.qumulo.utils.active_directory_api import ActiveDirectoryAPI

import sys


def update_user_with_additional_data(username: str, test_override=False) -> Optional[User]:
    # jprew - NOTE - adding this to avoid this running during tests
    # as it does not work locally
    if "test" in sys.argv and not test_override:
        return None

    # jprew - NOTE: at this point, I think the user *should* exist
    # since this is post_save
    # but I'll keep the user creation logic anyway
    should_update_or_create_user = False
    try:
        existing_user = User.objects.get(username=username)
        if (
            (existing_user.email is None or existing_user.email == "")
            or (existing_user.first_name is None or existing_user.first_name == "")
            or (existing_user.last_name is None or existing_user.last_name == "")
        ):
            should_update_or_create_user = True
    except User.DoesNotExist:
        should_update_or_create_user = True
    if should_update_or_create_user:
        active_directory_api = ActiveDirectoryAPI()
        attrs = active_directory_api.get_user(username)["attributes"]
        # either this user *already* exists with the specified username
        # or it doesn't
        user_tuple = User.objects.get_or_create(username=username)
        user = user_tuple[0]
        user.email = attrs["mail"]
        user.first_name = attrs["givenName"]
        user.last_name = attrs["sn"]
        user.save()
        # NOTE - returning user to make debugging easier
        # no code currently uses this returned value
        return user
