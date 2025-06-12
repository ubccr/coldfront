# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime

# import the logging library
import logging

from coldfront.core.allocation.models import Allocation, AllocationStatusChoice, AllocationUserStatusChoice
from coldfront.core.user.models import User
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template

# Get an instance of a logger
logger = logging.getLogger(__name__)


CENTER_NAME = import_from_settings("CENTER_NAME")
CENTER_BASE_URL = import_from_settings("CENTER_BASE_URL")
CENTER_PROJECT_RENEWAL_HELP_URL = import_from_settings("CENTER_PROJECT_RENEWAL_HELP_URL")
EMAIL_SENDER = import_from_settings("EMAIL_SENDER")
EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings("EMAIL_OPT_OUT_INSTRUCTION_URL")
EMAIL_SIGNATURE = import_from_settings("EMAIL_SIGNATURE")
EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS = import_from_settings(
    "EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS",
    [
        7,
    ],
)

EMAIL_ADMINS_ON_ALLOCATION_EXPIRE = import_from_settings("EMAIL_ADMINS_ON_ALLOCATION_EXPIRE")
EMAIL_ADMIN_LIST = import_from_settings("EMAIL_ADMIN_LIST")

EMAIL_ALLOCATION_EULA_IGNORE_OPT_OUT = import_from_settings("EMAIL_ALLOCATION_EULA_IGNORE_OPT_OUT")


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


def send_eula_reminders():
    for allocation in Allocation.objects.all():
        if allocation.get_eula():
            email_receiver_list = []
            for allocation_user in allocation.allocationuser_set.all():
                projectuser = allocation.project.projectuser_set.get(user=allocation_user.user)
                if (
                    allocation_user.status == AllocationUserStatusChoice.objects.get(name="PendingEULA")
                    and projectuser.status.name == "Active"
                ):
                    should_send = (projectuser.enable_notifications) or (EMAIL_ALLOCATION_EULA_IGNORE_OPT_OUT)
                    if should_send and allocation_user.user.email not in email_receiver_list:
                        email_receiver_list.append(allocation_user.user.email)

            template_context = {
                "center_name": CENTER_NAME,
                "resource": allocation.get_parent_resource,
                "url": f"{CENTER_BASE_URL.strip('/')}/{'allocation'}/{allocation.pk}/review-eula",
                "signature": EMAIL_SIGNATURE,
            }

            if email_receiver_list:
                send_email_template(
                    f"Reminder: Agree to EULA for {allocation}",
                    "email/allocation_eula_reminder.txt",
                    template_context,
                    EMAIL_SENDER,
                    email_receiver_list,
                )
                logger.debug(f"Allocation(s) EULA reminder sent to users {email_receiver_list}.")


def send_expiry_emails():
    # Allocations expiring soon
    for user in User.objects.all():
        projectdict = {}
        expirationdict = {}
        email_receiver_list = []
        for days_remaining in sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)):
            expring_in_days = (datetime.datetime.today() + datetime.timedelta(days=days_remaining)).date()

            for allocationuser in user.allocationuser_set.all():
                allocation = allocationuser.allocation

                if (allocation.status.name in ["Active", "Payment Pending", "Payment Requested", "Unpaid"]) and (
                    allocation.end_date == expring_in_days
                ):
                    project_url = f"{CENTER_BASE_URL.strip('/')}/{'project'}/{allocation.project.pk}/"

                    if allocation.status.name in ["Payment Pending", "Payment Requested", "Unpaid"]:
                        allocation_renew_url = f"{CENTER_BASE_URL.strip('/')}/{'allocation'}/{allocation.pk}/"
                    else:
                        allocation_renew_url = f"{CENTER_BASE_URL.strip('/')}/{'allocation'}/{allocation.pk}/{'renew'}/"

                    resource_name = allocation.get_parent_resource.name

                    template_context = {
                        "center_name": CENTER_NAME,
                        "expring_in_days": days_remaining,
                        "project_dict": projectdict,
                        "expiration_dict": expirationdict,
                        "expiration_days": sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)),
                        "project_renewal_help_url": CENTER_PROJECT_RENEWAL_HELP_URL,
                        "opt_out_instruction_url": EMAIL_OPT_OUT_INSTRUCTION_URL,
                        "signature": EMAIL_SIGNATURE,
                    }

                    expire_notification = allocation.allocationattribute_set.filter(
                        allocation_attribute_type__name="EXPIRE NOTIFICATION"
                    ).first()
                    if expire_notification and expire_notification.value == "No":
                        continue

                    cloud_usage_notification = allocation.allocationattribute_set.filter(
                        allocation_attribute_type__name="CLOUD_USAGE_NOTIFICATION"
                    ).first()
                    if cloud_usage_notification and cloud_usage_notification.value == "No":
                        continue

                    for projectuser in allocation.project.projectuser_set.filter(user=user, status__name="Active"):
                        if (projectuser.enable_notifications) and (
                            allocationuser.user == user and allocationuser.status.name == "Active"
                        ):
                            if user.email not in email_receiver_list:
                                email_receiver_list.append(user.email)

                            if days_remaining not in expirationdict:
                                expirationdict[days_remaining] = []
                                expirationdict[days_remaining].append(
                                    (project_url, allocation_renew_url, resource_name)
                                )
                            else:
                                expirationdict[days_remaining].append(
                                    (project_url, allocation_renew_url, resource_name)
                                )

                            if allocation.project.title not in projectdict:
                                projectdict[allocation.project.title] = (
                                    project_url,
                                    allocation.project.pi.username,
                                )

        if email_receiver_list:
            send_email_template(
                f"Your access to {CENTER_NAME}'s resources is expiring soon",
                "email/allocation_expiring.txt",
                template_context,
                EMAIL_SENDER,
                email_receiver_list,
            )

            logger.debug(f"Allocation(s) expiring in soon, email sent to user {user}.")

    # Allocations expired
    admin_projectdict = {}
    admin_allocationdict = {}
    for user in User.objects.all():
        projectdict = {}
        allocationdict = {}
        email_receiver_list = []

        expring_in_days = (datetime.datetime.today() + datetime.timedelta(days=-1)).date()

        for allocationuser in user.allocationuser_set.all():
            allocation = allocationuser.allocation

            if allocation.end_date == expring_in_days:
                project_url = f"{CENTER_BASE_URL.strip('/')}/{'project'}/{allocation.project.pk}/"

                allocation_renew_url = f"{CENTER_BASE_URL.strip('/')}/{'allocation'}/{allocation.pk}/{'renew'}/"

                allocation_url = f"{CENTER_BASE_URL.strip('/')}/{'allocation'}/{allocation.pk}/"

                resource_name = allocation.get_parent_resource.name

                template_context = {
                    "center_name": CENTER_NAME,
                    "project_dict": projectdict,
                    "allocation_dict": allocationdict,
                    "project_renewal_help_url": CENTER_PROJECT_RENEWAL_HELP_URL,
                    "opt_out_instruction_url": EMAIL_OPT_OUT_INSTRUCTION_URL,
                    "signature": EMAIL_SIGNATURE,
                }

                expire_notification = allocation.allocationattribute_set.filter(
                    allocation_attribute_type__name="EXPIRE NOTIFICATION"
                ).first()

                for projectuser in allocation.project.projectuser_set.filter(user=user, status__name="Active"):
                    if (projectuser.enable_notifications) and (
                        allocationuser.user == user and allocationuser.status.name == "Active"
                    ):
                        if expire_notification and expire_notification.value == "Yes":
                            if user.email not in email_receiver_list:
                                email_receiver_list.append(user.email)

                            if project_url not in allocationdict:
                                allocationdict[project_url] = []
                                allocationdict[project_url].append({allocation_renew_url: resource_name})
                            else:
                                if {allocation_renew_url: resource_name} not in allocationdict[project_url]:
                                    allocationdict[project_url].append({allocation_renew_url: resource_name})

                            if allocation.project.title not in projectdict:
                                projectdict[allocation.project.title] = (project_url, allocation.project.pi.username)

                        if EMAIL_ADMINS_ON_ALLOCATION_EXPIRE:
                            if project_url not in admin_allocationdict:
                                admin_allocationdict[project_url] = []
                                admin_allocationdict[project_url].append({allocation_url: resource_name})
                            else:
                                if {allocation_url: resource_name} not in admin_allocationdict[project_url]:
                                    admin_allocationdict[project_url].append({allocation_url: resource_name})

                            if allocation.project.title not in admin_projectdict:
                                admin_projectdict[allocation.project.title] = (
                                    project_url,
                                    allocation.project.pi.username,
                                )

        if email_receiver_list:
            send_email_template(
                "Your access to resource(s) have expired",
                "email/allocation_expired.txt",
                template_context,
                EMAIL_SENDER,
                email_receiver_list,
            )

            logger.debug(f"Allocation(s) expired email sent to user {user}.")

    if EMAIL_ADMINS_ON_ALLOCATION_EXPIRE:
        if admin_projectdict:
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
                [
                    EMAIL_ADMIN_LIST,
                ],
            )
