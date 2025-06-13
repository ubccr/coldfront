import json
import logging
import os

from django.core.management.base import BaseCommand
from coldfront.core.school.models import School
from coldfront.core.user.models import UserProfile, ApproverProfile
from django.contrib.auth.models import User, Permission

logger = logging.getLogger(__name__)

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
            logger.info(f"User {approver_username} not found. Skipping.")
            continue  # Skip to the next user

        # Get UserProfile for the user
        user_profile = UserProfile.objects.filter(user=user).first()

        # Grant 'can_review_allocation_requests' permission if not already granted
        perm_codename = "can_review_allocation_requests"
        perm = Permission.objects.filter(codename=perm_codename).first()

        if perm and not user.has_perm(f"allocation.{perm_codename}"):
            user.user_permissions.add(perm)
            user.save()
            logger.info(f"Granted '{perm_codename}' permission to {approver_username}")

        # Ensure user is an approver
        if not user_profile.is_approver():
            logger.info(
                f"Skipping {approver_username}: User does not have approver permission."
            )
            continue

        # Create ApproverProfile if it does not exist
        approver_profile, created = ApproverProfile.objects.get_or_create(
            user_profile=user_profile
        )

        # Ensure all schools exist before assigning
        school_objects = [
            School.objects.get_or_create(description=desc)[0]
            for desc in school_descriptions
        ]

        # Update schools for the approver
        approver_profile.schools.set(school_objects)
        approver_profile.save()

        logger.info(f"Updated {approver_username} with schools: {school_descriptions}")


class Command(BaseCommand):
    help = "Import approver-school mappings from JSON"

    def add_arguments(self, parser):
        default_path = os.path.join(
            app_commands_dir, "data", "approver_schools_data.json"
        )
        parser.add_argument(
            "--json-file-path",
            type=str,
            default=default_path,
            help="Path to approver_schools_data.json",
        )

    def handle(self, *args, **options):
        json_file_path = options["json_file_path"]
        self.stdout.write(f"Loading approver-school data from {json_file_path}…")

        with open(json_file_path, "r", encoding="utf-8") as fp:
            json_data = json.load(fp)
            load_approver_schools(json_data)

        self.stdout.write(self.style.SUCCESS("Finished adding approvers."))
