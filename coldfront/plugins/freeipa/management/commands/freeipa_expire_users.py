# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime
import logging
import os
import sys

import dbus
from django.core.management.base import BaseCommand
from django.urls import reverse
from ipalib import api

from coldfront.core.allocation.models import AllocationUser
from coldfront.core.utils.mail import build_link
from coldfront.plugins.freeipa.utils import CLIENT_KTNAME, FREEIPA_NOOP

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Report users to expire in FreeIPA"

    def add_arguments(self, parser):
        parser.add_argument("-s", "--sync", help="Sync changes to/from FreeIPA", action="store_true")
        parser.add_argument("-x", "--header", help="Include header in output", action="store_true")
        parser.add_argument("-n", "--noop", help="Print commands only. Do not run any commands.", action="store_true")

    def writerow(self, row):
        try:
            self.stdout.write("{0: <20}{1: <15}{2}".format(*row))
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)

    def handle(self, *args, **options):
        os.environ["KRB5_CLIENT_KTNAME"] = CLIENT_KTNAME

        verbosity = int(options["verbosity"])
        root_logger = logging.getLogger("")
        if verbosity == 0:
            root_logger.setLevel(logging.ERROR)
        elif verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.WARNING)

        self.sync = False
        if options["sync"]:
            self.sync = True
            logger.warning("Syncing FreeIPA with ColdFront")

        self.noop = FREEIPA_NOOP
        if options["noop"]:
            self.noop = True
            logger.warning("NOOP enabled")

        header = [
            "username",
            "expire_date",
            "allocation",
        ]

        if options["header"]:
            self.writerow(header)

        bus = dbus.SystemBus()
        infopipe_obj = bus.get_object("org.freedesktop.sssd.infopipe", "/org/freedesktop/sssd/infopipe")
        ifp = dbus.Interface(infopipe_obj, dbus_interface="org.freedesktop.sssd.infopipe")

        expired_365_days_ago = datetime.datetime.today() - datetime.timedelta(days=365)
        expired_365_days_ago = expired_365_days_ago.date()

        # Find all active users on active allocations
        active_users = sorted(
            list(
                set(
                    AllocationUser.objects.filter(status__name="Active")
                    .exclude(allocation__status__name__in=["Expired"])
                    .values_list("user__username", flat=True)
                )
            )
        )

        # Filter out users to expire, either not active or have been removed
        expired_allocation_users = {}
        for allocationuser in AllocationUser.objects.all():
            if allocationuser.user.username in active_users:
                continue

            allocation = allocationuser.allocation
            expire_date = allocation.end_date
            if allocation.status.name != "Expired" and allocationuser.status.name == "Removed":
                expire_date = allocationuser.modified.date()

            if not expire_date:
                logger.info(
                    "Unable to find expire date for user=%s allocation_id=%s",
                    allocationuser.user.username,
                    allocation.id,
                )
                continue

            if allocationuser.user.username not in expired_allocation_users:
                expired_allocation_users[allocationuser.user.username] = {
                    "user": allocationuser.user,
                    "expire_date": expire_date,
                    "allocation_id": allocation.id,
                }
            else:
                if expire_date > expired_allocation_users[allocationuser.user.username]["expire_date"]:
                    expired_allocation_users[allocationuser.user.username] = {
                        "user": allocationuser.user,
                        "expire_date": expire_date,
                        "allocation_id": allocation.id,
                    }

        # Print users whose latest allocation expiration date GTE 365 days and active in FreeIPA
        for key in expired_allocation_users.keys():
            if expired_allocation_users[key]["expire_date"] > expired_365_days_ago:
                continue

            try:
                result = ifp.GetUserAttr(key, ["nsaccountlock"])
                if "nsAccountLock" in result and str(result["nsAccountLock"][0]).lower() == "true":
                    # User is already disabled in FreeIPA so do nothing
                    logger.info("User already disabled in FreeIPA: %s", key)
                    pass
                else:
                    # User is active in FreeIPA but not on any active allocations
                    self.writerow(
                        [
                            key,
                            expired_allocation_users[key]["expire_date"].strftime("%Y-%m-%d"),
                            build_link(
                                reverse(
                                    "allocation-detail", kwargs={"pk": expired_allocation_users[key]["allocation_id"]}
                                )
                            ),
                        ]
                    )

                    if self.sync and not self.noop:
                        # Disable in ColdFront
                        expired_allocation_users[key]["user"].is_active = False
                        expired_allocation_users[key]["user"].save()

                        # Disable in FreeIPA
                        res = api.Command.user_disable(key)
                        if not res:
                            raise ValueError("Missing FreeIPA response")
                        if "result" not in res or not res["result"]:
                            raise ValueError(f"Failed to disable user: {res}")
            except dbus.exceptions.DBusException as e:
                if "No such user" in str(e) or "NotFound" in str(e):
                    logger.info("User %s not found in FreeIPA", key)
                else:
                    logger.error("dbus error failed to find user %s in FreeIPA: %s", key, e)
            except Exception as e:
                logger.error("Failed to disable user %s: %s", key, e)
