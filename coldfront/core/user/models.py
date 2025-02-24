from django.contrib.auth.models import User
from django.db import models
from coldfront.core.school.models import School


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
    def schools(self):
        """Get schools from ApproverProfile if the user is an approver."""
        default_schools = School.objects.none()
        if not hasattr(self, 'approver_profile'):
            return default_schools
        return self.approver_profile.schools.all()

    @schools.setter
    def schools(self, values):
        """Set schools in ApproverProfile if the user is an approver."""
        if self.is_approver():
            approver_profile, created = ApproverProfile.objects.get_or_create(user_profile=self)
            approver_profile.schools.set(School.objects.filter(description__in=values))
        else:
            raise ValueError("User is not an approver, cannot set schools.")


class ApproverProfile(models.Model):
    """Stores additional information for approvers."""
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="approver_profile")
    schools = models.ManyToManyField(School, blank=True)


