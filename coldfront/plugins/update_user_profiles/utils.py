from coldfront.core.user.models import UserProfile
from coldfront.plugins.ldap_user_info.utils import get_user_info, LDAPSearch


def update_all_user_profiles():
    """
    Updates all user profiles.
    """
    ldap_search = LDAPSearch()
    user_profiles = UserProfile.objects.all().prefetch_related('user')
    for user_profile in user_profiles:
        search_attributes = {'title': '', 'department': '', 'division': '', 'mail': ''}
        attributes = get_user_info(user_profile.user.username, list(search_attributes.keys()), ldap_search)

        for name, value in attributes.items():
            if value:
                search_attributes[name] = value[0]

        save_changes = False
        for name, value in search_attributes.items():
            if name == 'mail':
                if user_profile.user.email != value:
                    user_profile.user.email = value
                    user_profile.user.save()
            else:
                if getattr(user_profile, name) != value:
                    setattr(user_profile, name, value)
                    save_changes = True

        if save_changes:
            user_profile.save()
