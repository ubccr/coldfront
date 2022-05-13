from django.core.exceptions import BadRequest
from django.db.models.signals import pre_delete
import django.dispatch

from allauth.socialaccount.models import SocialAccount


@django.dispatch.receiver(pre_delete, sender=SocialAccount)
def prevent_user_last_social_account_deletion(sender, instance, **kwargs):
    """When a SocialAccount is about to be deleted, if it is its user's
    last one, raise an error."""
    user_other_social_accounts = SocialAccount.objects.filter(
        user=instance.user).exclude(pk=instance.pk)
    if not user_other_social_accounts.exists():
        raise BadRequest('You may not delete your last connected account.')
