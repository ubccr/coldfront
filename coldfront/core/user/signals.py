import logging
import json

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django_cas_ng.signals import cas_user_authenticated, cas_user_logout


from coldfront.core.user.models import UserProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
            from coldfront.plugins.ldap_user_info.utils import get_user_info
            attributes = get_user_info(
                instance.username, ['title', 'department', 'division', 'mail', 'sn', 'givenName']
            )

            title = ''
            if attributes['title']:
                title = attributes['title'][0]
            is_pi = True
            if title == 'group':
                is_pi = False

            department = ''
            if attributes['department']:
                department = attributes['department'][0]

            division = ''
            if attributes['division']:
                division = attributes['division'][0]

            UserProfile.objects.create(
                user=instance,
                title=title,
                department=department,
                division=division,
                is_pi=is_pi
            )

            if attributes['mail']:
                instance.email = attributes['mail'][0]
            if attributes['givenName']:
                instance.first_name = attributes['givenName'][0]
            if attributes['sn']:
                instance.last_name = attributes['sn'][0]
            instance.save()
        else:
            UserProfile.objects.create(
                user=instance,
                title='',
                department='',
                division='',
            )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()


@receiver(user_logged_in, sender=User)
def update_user_profile(sender, user, **kwargs):
    logger.info(f'{user.username} logged in')
    if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
        from coldfront.plugins.ldap_user_info.utils import get_user_info
        search_attributes = {'title': '', 'department': '', 'division': '', 'mail': ''}
        attributes = get_user_info(user.username, list(search_attributes.keys()))
        user_profile = UserProfile.objects.get(user=user)

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


@receiver(cas_user_authenticated)
def cas_user_authenticated_callback(sender, **kwargs):
    args = {}
    args.update(kwargs)
    print('''cas_user_authenticated_callback:
    user: %s
    created: %s
    attributes: %s
    ''' % (
        args.get('user'),
        args.get('created'),
        json.dumps(args.get('attributes'), sort_keys=True, indent=2)))


@receiver(cas_user_logout)
def cas_user_logout_callback(sender, **kwargs):
    args = {}
    args.update(kwargs)
    print('''cas_user_logout_callback:
    user: %s
    session: %s
    ticket: %s
    ''' % (
        args.get('user'),
        args.get('session'),
        args.get('ticket')))
