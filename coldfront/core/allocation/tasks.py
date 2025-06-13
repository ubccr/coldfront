import datetime

# import the logging library
import logging

from coldfront.core.allocation.models import Allocation, AllocationStatusChoice
from coldfront.core.user.models import User
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template
from django.utils import timezone

# Get an instance of a logger
logger = logging.getLogger(__name__)


CENTER_NAME = import_from_settings("CENTER_NAME")
CENTER_BASE_URL = import_from_settings("CENTER_BASE_URL")
CENTER_PROJECT_RENEWAL_HELP_URL = import_from_settings(
    "CENTER_PROJECT_RENEWAL_HELP_URL"
)
EMAIL_SENDER = import_from_settings("EMAIL_SENDER")
EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings("EMAIL_OPT_OUT_INSTRUCTION_URL")
EMAIL_SIGNATURE = import_from_settings("EMAIL_SIGNATURE")
EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS = import_from_settings(
    "EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS",
    [
        7,
    ],
)

EMAIL_ADMINS_ON_ALLOCATION_EXPIRE = import_from_settings(
    "EMAIL_ADMINS_ON_ALLOCATION_EXPIRE"
)
EMAIL_ADMIN_LIST = import_from_settings("EMAIL_ADMIN_LIST")


def update_statuses():
    expired_status_choice = AllocationStatusChoice.objects.get(name="Expired")
    allocations_to_expire = Allocation.objects.filter(
        status__name__in=[
            "Active",
            "Payment Pending",
            "Payment Requested",
            "Unpaid",
        ],
        end_date__lt=datetime.datetime.now().date(),
    )
    for sub_obj in allocations_to_expire:
        sub_obj.status = expired_status_choice
        sub_obj.save()

    logger.info("Allocations set to expired: {}".format(allocations_to_expire.count()))


def send_expiry_emails():
    send_expiring_mails()
    send_expired_mails()


def send_expiring_mails():
    # Build the set of target expiration dates
    today = timezone.now().date()
    target_dates = [
        today + datetime.timedelta(days=d)
        for d in EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS
    ]
    # Get allocations expiring soon
    expiring_allocations = Allocation.objects.filter(
        status__name__in=["Active", "Payment Pending", "Payment Requested", "Unpaid"],
        end_date__in=target_dates,
    )
    # Map: recipient email → list of allocation data
    recipient_to_allocations = {}
    for allocation in expiring_allocations:
        # Skip if EXPIRE NOTIFICATION is 'No'
        expire_notification = allocation.allocationattribute_set.filter(
            allocation_attribute_type__name="EXPIRE NOTIFICATION"
        ).first()
        if expire_notification and expire_notification.value == "No":
            continue

        # Skip if CLOUD USAGE NOTIFICATION is 'No'
        cloud_usage_notification = allocation.allocationattribute_set.filter(
            allocation_attribute_type__name="CLOUD USAGE NOTIFICATION"
        ).first()
        if cloud_usage_notification and cloud_usage_notification.value == "No":
            continue

        allocation_school = allocation.project.school
        project_url = f"{CENTER_BASE_URL.strip('/')}/project/{allocation.project.pk}/"
        resource_name = allocation.get_parent_resource.name

        if allocation.status.name in ["Payment Pending", "Payment Requested", "Unpaid"]:
            allocation_renew_url = (
                f"{CENTER_BASE_URL.strip('/')}/allocation/{allocation.pk}/"
            )
        else:
            allocation_renew_url = (
                f"{CENTER_BASE_URL.strip('/')}/allocation/{allocation.pk}/renew/"
            )

        days_remaining = (allocation.end_date - today).days

        # Get relevant approvers
        approvers = User.objects.filter(
            userprofile__approver_profile__schools=allocation_school, is_active=True
        ).distinct()

        # Build the recipient list (approvers + PI + project manager(s))
        recipient_emails = set()

        # Add approvers
        for approver in approvers:
            if approver.email:
                recipient_emails.add(approver.email)

        # Add PI
        if allocation.project.pi and allocation.project.pi.email:
            recipient_emails.add(allocation.project.pi.email)

        # Add project manager(s)
        manager_users = allocation.project.projectuser_set.filter(
            role__name="Manager",
            status__name__in=["Active", "New"],
            user__is_active=True,
        ).select_related("user")

        for project_user in manager_users:
            if project_user.user.email:
                recipient_emails.add(project_user.user.email)

        for email in recipient_emails:
            if email not in recipient_to_allocations:
                recipient_to_allocations[email] = []

            recipient_to_allocations[email].append(
                {
                    "days_remaining": days_remaining,
                    "project_title": allocation.project.title,
                    "project_url": project_url,
                    "resource_name": resource_name,
                    "allocation_renew_url": allocation_renew_url,
                    "pi_username": allocation.project.pi.username,
                }
            )
    # Send email to each recipient
    for email, allocations in recipient_to_allocations.items():
        expirationdict = {}
        projectdict = {}

        for entry in allocations:
            days = entry["days_remaining"]
            expirationdict.setdefault(days, []).append(
                (
                    entry["project_url"],
                    entry["allocation_renew_url"],
                    entry["resource_name"],
                )
            )
            projectdict.setdefault(
                entry["project_title"], (entry["project_url"], entry["pi_username"])
            )

        template_context = {
            "center_name": CENTER_NAME,
            "expiration_days": sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)),
            "expring_in_days": sorted(expirationdict.keys()),
            "expiration_dict": expirationdict,
            "project_dict": projectdict,
            "project_renewal_help_url": CENTER_PROJECT_RENEWAL_HELP_URL,
            "opt_out_instruction_url": EMAIL_OPT_OUT_INSTRUCTION_URL,
            "signature": EMAIL_SIGNATURE,
        }
        send_email_template(
            f"Allocations expiring soon in {CENTER_NAME}",
            "email/allocation_expiring.txt",
            template_context,
            EMAIL_SENDER,
            [email],
        )

        logger.debug(f"Allocation(s) expiring in soon, email sent to user {email}.")


def send_expired_mails():
    # Set target date: yesterday
    expired_date = timezone.now().date() - datetime.timedelta(days=1)
    # Get allocations that expired yesterday
    expired_allocations = Allocation.objects.filter(end_date=expired_date)
    # Map: recipient email → {project_dict, allocation_dict}
    recipient_to_allocations = {}
    # Admin grouping
    admin_projectdict = {}
    admin_allocationdict = {}
    for allocation in expired_allocations:
        # Respect EXPIRE NOTIFICATION opt-out
        expire_notification = allocation.allocationattribute_set.filter(
            allocation_attribute_type__name="EXPIRE NOTIFICATION"
        ).first()
        if expire_notification and expire_notification.value == "No":
            continue

        allocation_school = allocation.project.school
        project_url = f"{CENTER_BASE_URL.strip('/')}/project/{allocation.project.pk}/"
        allocation_renew_url = (
            f"{CENTER_BASE_URL.strip('/')}/allocation/{allocation.pk}/renew/"
        )
        allocation_url = f"{CENTER_BASE_URL.strip('/')}/allocation/{allocation.pk}/"
        resource_name = allocation.get_parent_resource.name

        # Get relevant approvers based on school
        approvers = User.objects.filter(
            userprofile__approver_profile__schools=allocation_school, is_active=True
        ).distinct()

        # Build the recipient list (approvers + PI + project manager(s))
        recipient_emails = set()

        # Add approvers
        for approver in approvers:
            if approver.email:
                recipient_emails.add(approver.email)

        # Add PI
        if allocation.project.pi and allocation.project.pi.email:
            recipient_emails.add(allocation.project.pi.email)

        # Add project manager(s)
        manager_users = allocation.project.projectuser_set.filter(
            role__name="Manager",
            status__name__in=["Active", "New"],
            user__is_active=True,
        ).select_related("user")

        for project_user in manager_users:
            if project_user.user.email:
                recipient_emails.add(project_user.user.email)

        for email in recipient_emails:
            if email not in recipient_to_allocations:
                recipient_to_allocations[email] = {
                    "project_dict": {},
                    "allocation_dict": {},
                }

            # Append allocation info
            projectdict = recipient_to_allocations[email]["project_dict"]
            allocationdict = recipient_to_allocations[email]["allocation_dict"]

            allocationdict.setdefault(project_url, []).append(
                {allocation_renew_url: resource_name}
            )
            projectdict.setdefault(
                allocation.project.title, (project_url, allocation.project.pi.username)
            )

        # Admins still get full summary
        if EMAIL_ADMINS_ON_ALLOCATION_EXPIRE:
            admin_allocationdict.setdefault(project_url, []).append(
                {allocation_url: resource_name}
            )
            admin_projectdict.setdefault(
                allocation.project.title, (project_url, allocation.project.pi.username)
            )
    # Send expired emails per recipient
    for email, context_data in recipient_to_allocations.items():
        template_context = {
            "center_name": CENTER_NAME,
            "project_dict": context_data["project_dict"],
            "allocation_dict": context_data["allocation_dict"],
            "project_renewal_help_url": CENTER_PROJECT_RENEWAL_HELP_URL,
            "opt_out_instruction_url": EMAIL_OPT_OUT_INSTRUCTION_URL,
            "signature": EMAIL_SIGNATURE,
        }

        send_email_template(
            "Your access to resource(s) has expired",
            "email/allocation_expired.txt",
            template_context,
            EMAIL_SENDER,
            [email],
        )

        logger.debug(f"Allocation(s) expired email sent to user {email}.")
    # Send summary to admins
    if EMAIL_ADMINS_ON_ALLOCATION_EXPIRE and admin_projectdict:
        admin_template_context = {
            "project_dict": admin_projectdict,
            "allocation_dict": admin_allocationdict,
            "signature": EMAIL_SIGNATURE,
        }

        send_email_template(
            "Allocation(s) have expired",
            "email/admin_allocation_expired.txt",
            admin_template_context,
            EMAIL_SENDER,
            [EMAIL_ADMIN_LIST],
        )
