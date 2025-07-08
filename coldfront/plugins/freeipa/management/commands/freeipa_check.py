# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import sys

import dbus
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from ipalib import api

from coldfront.core.allocation.models import AllocationUser, AllocationUserStatusChoice
from coldfront.core.project.models import ProjectUser, ProjectUserStatusChoice
from coldfront.plugins.freeipa.search import LDAPUserSearch
from coldfront.plugins.freeipa.utils import (
    CLIENT_KTNAME,
    FREEIPA_NOOP,
    UNIX_GROUP_ATTRIBUTE_NAME,
    AlreadyMemberError,
    NotMemberError,
    check_ipa_group_error,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync groups in FreeIPA"

    def add_arguments(self, parser):
        parser.add_argument("-s", "--sync", help="Sync changes to/from FreeIPA", action="store_true")
        parser.add_argument("-u", "--username", help="Check specific username")
        parser.add_argument("-g", "--group", help="Check specific group")
        parser.add_argument(
            "-d",
            "--disable",
            help="Disable users in ColdFront that are Disabled/NotFound in FreeIPA",
            action="store_true",
        )
        parser.add_argument("-n", "--noop", help="Print commands only. Do not run any commands.", action="store_true")
        parser.add_argument("-x", "--header", help="Include header in output", action="store_true")

    def writerow(self, row):
        try:
            self.stdout.write("{0: <12}{1: <20}{2: <30}{3}".format(*row))
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)

    def check_ipa_error(self, res):
        if not res or "result" not in res:
            raise ValueError("Missing FreeIPA result")

    def add_group(self, user, group, status):
        if self.sync and not self.noop:
            try:
                res = api.Command.group_add_member(group, user=[user.username])
                check_ipa_group_error(res)
            except AlreadyMemberError:
                logger.warning("User %s is already a member of group %s", user.username, group)
            except Exception as e:
                logger.error("Failed adding user %s to group %s: %s", user.username, group, e)
            else:
                logger.info("Added user %s to group %s successfully", user.username, group)

        row = [
            "Add",
            user.username,
            group,
            "/".join([status, "Active" if user.is_active else "Inactive"]),
        ]

        self.writerow(row)

    def remove_group(self, user, group, status):
        if self.sync and not self.noop:
            try:
                res = api.Command.group_remove_member(group, user=[user.username])
                check_ipa_group_error(res)
            except NotMemberError:
                logger.warning("User %s is not a member of group %s", user.username, group)
            except Exception as e:
                logger.error("Failed removing user %s from group %s: %s", user.username, group, e)
            else:
                logger.info("Removed user %s from group %s successfully", user.username, group)

        row = [
            "Remove",
            user.username,
            group,
            "/".join([status, "Active" if user.is_active else "Inactive"]),
        ]

        self.writerow(row)

    def disable_user_in_coldfront(self, user, freeipa_status):
        row = [
            "Disable",
            user.username,
            "",
            "/".join([freeipa_status, "Active" if user.is_active else "Inactive"]),
        ]
        self.writerow(row)

        if not self.sync:
            return

        if self.noop:
            return

        # Disable user from any active allocations
        inactive_status = AllocationUserStatusChoice.objects.get(name="Removed")
        user_allocations = AllocationUser.objects.filter(user=user)
        for ua in user_allocations:
            if ua.status.name == "Active" and ua.allocation.status.name == "Active":
                logger.info("Removing user from allocation user=%s allocation=%s", user.username, ua.allocation)
                ua.status = inactive_status
                ua.save()

        # Disable user from any active projects
        inactive_status = ProjectUserStatusChoice.objects.get(name="Removed")
        user_projects = ProjectUser.objects.filter(user=user)
        for pa in user_projects:
            if pa.status.name == "Active" and pa.project.status.name == "Active":
                logger.info("Removing user from project user=%s project=%s", user.username, pa.project)
                pa.status = inactive_status
                pa.save()

        self.sync_user_status(user, active=False)

    def sync_user_status(self, user, active=False):
        if not self.sync:
            return

        if self.noop:
            return

        try:
            user.is_active = active
            user.save()
        except Exception as e:
            logger.error("Failed to update user status: %s - %s", user.username, e)

    def check_user_freeipa(self, user, active_groups, removed_groups):
        logger.info(
            "Checking FreeIPA user=%s active_groups=%s removed_groups=%s", user.username, active_groups, removed_groups
        )

        freeipa_groups = []
        freeipa_status = "Unknown"
        try:
            result = self.ifp.GetUserGroups(user.username)
            logger.debug(result)
            freeipa_groups = [str(x) for x in result]

            users = self.ipa_ldap.search_a_user(user.username, "username_only")
            if len(users) == 1:
                freeipa_status = "Enabled"
            else:
                freeipa_status = "Disabled"
        except dbus.exceptions.DBusException as e:
            if "No such user" in str(e) or "NotFound" in str(e):
                logger.info("Skipping user %s not found in FreeIPA", user.username)
                freeipa_status = "NotFound"
            else:
                logger.error("dbus error failed to find user %s in FreeIPA: %s", user.username, e)
            return

        if freeipa_status == "Disabled" and user.is_active:
            logger.warning("User is active in coldfront but disabled in FreeIPA: %s", user.username)
            self.sync_user_status(user, active=False)
        elif freeipa_status == "Enabled" and not user.is_active:
            logger.warning("User is not active in coldfront but enabled in FreeIPA: %s", user.username)
            self.sync_user_status(user, active=True)

        for g in active_groups:
            if g not in freeipa_groups:
                logger.info("User %s should be added to freeipa group: %s", user.username, g)
                self.add_group(user, g, freeipa_status)

        for g in removed_groups:
            if g in freeipa_groups:
                logger.info("User %s should be removed from freeipa group: %s", user.username, g)
                self.remove_group(user, g, freeipa_status)

    def process_user(self, user):
        if self.filter_user and self.filter_user != user.username:
            return

        user_allocations = AllocationUser.objects.filter(
            user=user, allocation__allocationattribute__allocation_attribute_type__name=UNIX_GROUP_ATTRIBUTE_NAME
        )

        active_groups = []
        for ua in user_allocations:
            if not ua.is_active():
                continue

            all_resources_inactive = True
            for r in ua.allocation.resources.all():
                if r.is_available:
                    all_resources_inactive = False

            if all_resources_inactive:
                logger.debug(
                    "Skipping allocation to %s for user %s due to all resources being inactive",
                    ua.allocation.get_resources_as_string,
                    user.username,
                )
                continue

            for g in ua.allocation.get_attribute_list(UNIX_GROUP_ATTRIBUTE_NAME):
                if g not in active_groups:
                    active_groups.append(g)

        removed_groups = []
        for ua in user_allocations:
            if ua.is_active():
                continue

            for g in ua.allocation.get_attribute_list(UNIX_GROUP_ATTRIBUTE_NAME):
                if g not in removed_groups and g not in active_groups:
                    removed_groups.append(g)

        if self.filter_group:
            if self.filter_group in active_groups:
                active_groups = [self.filter_group]
            else:
                active_groups = []

            if self.filter_group in removed_groups:
                removed_groups = [self.filter_group]
            else:
                removed_groups = []

        if len(active_groups) == 0 and len(removed_groups) == 0:
            return

        self.check_user_freeipa(user, active_groups, removed_groups)

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

        self.noop = FREEIPA_NOOP
        if options["noop"]:
            self.noop = True
            logger.warning("NOOP enabled")

        self.sync = False
        if options["sync"]:
            self.sync = True
            logger.warning("Syncing FreeIPA with ColdFront")

        self.disable = False
        if options["disable"]:
            self.disable = True
            logger.warning("Disabling users in ColdFront that are disabled in FreeIPA")

        header = [
            "action",
            "username",
            "group",
            "ipa/cf",
        ]

        if options["header"]:
            self.writerow(header)

        self.ipa_ldap = LDAPUserSearch("", "")
        bus = dbus.SystemBus()
        infopipe_obj = bus.get_object("org.freedesktop.sssd.infopipe", "/org/freedesktop/sssd/infopipe")
        self.ifp = dbus.Interface(infopipe_obj, dbus_interface="org.freedesktop.sssd.infopipe")

        users = User.objects.filter(is_active=True)
        logger.info("Processing %s active users", len(users))

        self.filter_user = ""
        self.filter_group = ""
        if options["username"]:
            logger.info("Filtering output by username: %s", options["username"])
            self.filter_user = options["username"]
        if options["group"]:
            logger.info("Filtering output by group: %s", options["group"])
            self.filter_group = options["group"]

        for user in users:
            self.process_user(user)

        if self.disable:
            for user in users:
                if self.filter_user and self.filter_user != user.username:
                    continue

                try:
                    result = self.ifp.GetUserAttr(user.username, ["nsaccountlock"])
                    if "nsAccountLock" in result and str(result["nsAccountLock"][0]) == "TRUE":
                        # User is disabled in FreeIPA so disable in coldfront
                        logger.info("User is disabled in FreeIPA so disable in ColdFront: %s", user.username)
                        self.disable_user_in_coldfront(user, "Disabled")
                except dbus.exceptions.DBusException as e:
                    if "No such user" in str(e) or "NotFound" in str(e):
                        # User is not found in FreeIPA so disable in coldfront
                        logger.info("User is not found in FreeIPA so disable in ColdFront: %s", user.username)
                        self.disable_user_in_coldfront(user, "NotFound")
                    else:
                        logger.error("dbus error failed while checking user %s in FreeIPA: %s", user.username, e)
