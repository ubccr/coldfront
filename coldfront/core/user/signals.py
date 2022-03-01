import logging

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from coldfront.core.user.models import UserProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
            from coldfront.plugins.ldap_user_info.utils import get_user_info
            attributes = get_user_info(instance.username, ['title', 'department'])

            title = attributes['title'][0]
            max_projects = 0
            if title in ['Faculty', 'Staff', 'Academic (ACNP)', 'Affiliate', 'Regular Hourly', ]:
                max_projects = 2
            elif title in ['Graduate', 'Student Hourly']:
                max_projects = 1
            else:
                logger.error(
                    'Max projects not set for title: {}'.format(title)
                )
                max_projects = -1

            UserProfile.objects.create(
                user=instance,
                title=title,
                department=attributes['department'][0],
                max_projects=max_projects
            )
        else:
            UserProfile.objects.create(
                user=instance,
                title='',
                department='',
                max_projects=1
            )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
        from coldfront.plugins.ldap_user_info.utils import get_user_info
        attributes = get_user_info(instance.username, ['title', 'department'])
        instance.userprofile.title = attributes['title'][0]
        instance.userprofile.department = attributes['department'][0]

    instance.userprofile.save()
