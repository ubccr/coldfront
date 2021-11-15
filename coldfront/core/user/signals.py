import logging

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from coldfront.core.user.models import UserProfile
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        ldap_search = import_string('coldfront.plugins.ldap_user_search.utils.LDAPSearch')
        search_class_obj = ldap_search()
        attributes = search_class_obj.search_a_user(instance.username, ['title', 'department'])
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


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    ldap_search = import_string('coldfront.plugins.ldap_user_search.utils.LDAPSearch')
    search_class_obj = ldap_search()
    attributes = search_class_obj.search_a_user(instance.username, ['title', 'department'])
    instance.userprofile.title = attributes['title'][0]
    instance.userprofile.department = attributes['department'][0]
    instance.userprofile.save()
