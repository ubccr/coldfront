from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """ Displays a user's profile. A user can be a principal investigator (PI), manager, administrator, staff member, billing staff member, or center director.

    Attributes:
        is_pi (bool): indicates whether or not the user is a PI
        user (User): represents the Django User model    
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_pi = models.BooleanField(default=False)

    def is_approver(self):
        """Checks if the user has the 'can_review_allocation_requests' permission."""
        return self.user.has_perm('allocation.can_review_allocation_requests')

    @property
    def school(self):
        """Get school from ApproverProfile if the user is an approver."""
        if hasattr(self, 'approver_profile'):
            return self.approver_profile.school
        return None

    @school.setter
    def school(self, value):
        """Set school in ApproverProfile if the user is an approver."""
        if self.is_approver():
            approver_profile, created = ApproverProfile.objects.get_or_create(user_profile=self)
            approver_profile.school = value
            approver_profile.save()
        else:
            raise ValueError("User is not an approver, cannot set school.")


class ApproverProfile(models.Model):
    """Stores additional information for approvers.

    Attributes:
        user_profile (UserProfile): Links to the base user profile.
        school (str): Represents the school associated with the approver.
    """
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="approver_profile")
    school = models.CharField(max_length=255, blank=True, null=True)

