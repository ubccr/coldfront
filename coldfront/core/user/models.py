from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """ Displays a user's profile. A user can be a principal investigator (PI), manager, administrator, staff member, billing staff member, or center director.

    Attributes:
        is_pi (bool): indicates whether or not the user is a PI
        user (User): represents the Django User model
        department (str): the department the user is in
        division (str): the department code
        title (str): the user's status
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_pi = models.BooleanField(default=False)
    department = models.CharField(max_length=100, default='')
    division = models.CharField(max_length=100, default='')
    title = models.CharField(max_length=30, default='')
