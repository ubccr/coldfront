from django.contrib.auth.models import User
from django.db import models

from coldfront.core.organization.models import Organization

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_pi = models.BooleanField(default=False)
    organizations = models.ManyToManyField(Organization,
            related_name='users')

    def __str__(self):
        return 'Profile for {}'.format(self.user.username)


