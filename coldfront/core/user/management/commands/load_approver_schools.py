import json
import os

from django.core.management.base import BaseCommand
from coldfront.core.school.models import School
from coldfront.core.user.models import UserProfile, ApproverProfile
from django.contrib.auth.models import User, Permission

app_commands_dir = os.path.dirname(__file__)


def load_approver_schools(json_data):
    """
    Grant is_staff, approver_profile, "can_review_allocation_requests" permission associated with schools
    """
    for approver_username, school_descriptions in json_data.items():
        try:
            # Check if the user exists
            user = User.objects.get(username=approver_username)
            # Make as a staff to let an approver view admin navigation bar
            user.is_staff = True
            user.save()
        except User.DoesNotExist:
            # print(f"User {approver_username} not found. Skipping.")
            continue  # Skip to the next user

        # Get UserProfile for the user
        user_profile = UserProfile.objects.filter(user=user).first()

        # Grant 'can_review_allocation_requests' permission if not already granted
        perm_codename = "can_review_allocation_requests"
        perm = Permission.objects.filter(codename=perm_codename).first()

        if perm and not user.has_perm(f"allocation.{perm_codename}"):
            user.user_permissions.add(perm)
            user.save()
            # print(f"Granted '{perm_codename}' permission to {approver_username}")

        # Ensure user is an approver
        if not user_profile.is_approver():
            # print(f"Skipping {approver_username}: User does not have approver permission.")
            continue

        # Create ApproverProfile if it does not exist
        approver_profile, created = ApproverProfile.objects.get_or_create(user_profile=user_profile)

        # Ensure all schools exist before assigning
        school_objects = [School.objects.get_or_create(description=desc)[0] for desc in school_descriptions]

        # Update schools for the approver
        approver_profile.schools.set(school_objects)
        approver_profile.save()

        # print(f"Updated {approver_username} with schools: {school_descriptions}")



class Command(BaseCommand):
    help = 'Import school data'

    def handle(self, *args, **options):
        print('Adding schools ...')
        json_file_path = os.path.join(app_commands_dir, 'data', 'approver_schools_data.json')
        with open(json_file_path, "r") as file:
            json_data = json.load(file)
            load_approver_schools(json_data)

        print('Finished adding approvers')
