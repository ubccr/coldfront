from django.contrib.auth.models import User, Group
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from coldfront.core.user.models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()


@receiver(post_save, sender=User)
def give_staff_group(sender, instance, **kwargs):
    if not instance.is_superuser:
        try:
            group_name = 'staff_group'
            group = Group.objects.get(name=group_name)

            if instance.is_staff and not instance.groups.filter(name=group_name).exists():
                instance.groups.add(group)
            elif not instance.is_staff and instance.groups.filter(name=group_name).exists():
                instance.groups.remove(group)
        except Group.DoesNotExist:
            raise LookupError('Queried staff group does not exist. Examine core/user/signals.py')


@receiver(m2m_changed, sender=User.groups.through)
def sync_staff_to_group(instance, action, **kwargs):
    if not instance.is_superuser:
        try:
            if action == 'post_remove' or action == 'post_add' or action == 'post_clear':
                group_name = 'staff_group'
                group = Group.objects.get(name=group_name)

                if instance.is_staff and not instance.groups.filter(name=group_name).exists():
                    instance.groups.add(group)
                elif not instance.is_staff and instance.groups.filter(name=group_name).exists():
                    instance.groups.remove(group)
        except Group.DoesNotExist:
            raise LookupError('Queried staff group does not exist. Examine core/user/signals.py')
