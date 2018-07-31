from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from common.djangoapps.user.models import UserProfile


@receiver(user_logged_in)
def update_pi_status(sender, request, user, **kwargs):
    if 'pi' in user.groups.all().values_list('name', flat=True):
        user.userprofile.is_pi = True
        user.save()
    else:
        user.userprofile.is_pi = False
        user.save()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()
