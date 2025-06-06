# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront project_openldap plugin - django management command -  project_openldap_sync.py"""

import logging
import sys

from django.core.management.base import BaseCommand

# OpenLDAP (ldap3) connections formed in utils.py

from coldfront.core.utils.common import import_from_settings
from coldfront.core.project.models import (
    Project,
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserStatusChoice,
)

# this script relies HEAVILY on utils.py
from coldfront.plugins.project_openldap.utils import (
    add_members_to_openldap_project_posixgroup,
    add_per_project_ou_to_openldap,
    add_project_posixgroup_to_openldap,
    allocate_project_openldap_gid,
    archive_project_in_openldap,
    construct_dn_archived_str,
    construct_ou_archived_dn_str,
    construct_dn_str,
    construct_ou_dn_str,
    construct_per_project_ou_relative_dn_str,
    construct_project_posixgroup_description,
    construct_project_ou_description,
    ldapsearch_check_project_dn,
    ldapsearch_get_project_description,
    ldapsearch_get_project_memberuids,
    remove_members_from_openldap_project_posixgroup,
    update_project_posixgroup_in_openldap,
)

# NEW or ACTIVE status projects not known to OpenLDAP at all can simply be added as normal, using tasks.py function
# Normal deletion also handled by tasks.py method
from coldfront.plugins.project_openldap.tasks import add_project, remove_project

# NOTE: functions starting with 'local_' or 'handle_' are local to this script

PROJECT_CODE = import_from_settings("PROJECT_CODE")

PROJECT_OPENLDAP_GID_START = import_from_settings("PROJECT_OPENLDAP_GID_START")
PROJECT_OPENLDAP_OU = import_from_settings("PROJECT_OPENLDAP_OU")
PROJECT_OPENLDAP_REMOVE_PROJECT = import_from_settings(
    "PROJECT_OPENLDAP_REMOVE_PROJECT"
)
PROJECT_OPENLDAP_ARCHIVE_OU = import_from_settings("PROJECT_OPENLDAP_ARCHIVE_OU")

PROJECT_OPENLDAP_EXCLUDE_USERS = import_from_settings("PROJECT_OPENLDAP_EXCLUDE_USERS")

logger = logging.getLogger(__name__)

# affirm project status choices
PROJECT_STATUS_CHOICE_NEW = ProjectStatusChoice.objects.get(name="New").pk
PROJECT_STATUS_CHOICE_ACTIVE = ProjectStatusChoice.objects.get(name="Active").pk
PROJECT_STATUS_CHOICE_ARCHIVED = ProjectStatusChoice.objects.get(name="Archived").pk
# affirm project user status choices
PROJECTUSER_STATUS_CHOICE_ACTIVE = ProjectUserStatusChoice.objects.get(name="Active").pk

# where project_dn var is used -> posixgroup DN
# where archive_dn var is used -> posixgroup DN in archive
# where DN var is used, can be any DN
# where DNs are passed to functions it is oftern to print before an action


# --------------------------------------------------------------------------------------------------------


def local_get_project_by_code(project_group):
    try:
        return Project.objects.get(project_code__iexact=project_group)
    except Project.DoesNotExist:
        print(f"Project group: {project_group} is not in Coldfront Django!!!")
        return None


def handle_missing_project_in_openldap_new_active(project, sync=False):
    # if sync, can write
    if sync:
        # simply add the project using tasks.py function
        add_project(project)
    # else notify, need to write with sync
    else:
        print(
            f"Project DN for {project.project_code} is MISSING from OpenLDAP - SYNC is {sync} - WILL NOT WRITE TO OpenLDAP"
        )


def handle_missing_project_in_openldap_archive(
    project, project_dn, sync=False, write_to_archive=False
):
    # setup vars before anything else
    try:
        # create ou vars
        archive_openldap_ou_description = construct_project_ou_description(project)
        archive_ou_dn = construct_ou_archived_dn_str(project)

        # create posixgroup vars
        archive_gid = allocate_project_openldap_gid(
            project.pk, PROJECT_OPENLDAP_GID_START
        )
        archive_openldap_posixgroup_description = (
            construct_project_posixgroup_description(project)
        )
        archive_posixgroup_dn = construct_dn_archived_str(project)
    except Exception as e:
        print(
            f"Exception creating vars for OpenLDAP archive action for Project {project.project_code}: {e}"
        )

    # if sync not permitted, notify, DN is passed to function here
    if not sync:
        print(
            f"{project_dn} <<< WARNING WE EXPECTED THIS TO BE ARCHIVED IN OPENLDAP - PROJECT_OPENLDAP_ARCHIVE_OU is set"
        )
        print(f"{archive_posixgroup_dn} is the expected DN")
        print(f"Project {project.project_code} - Corrective action may be required")
    # if sync permitted but writing to archive not permitted, notify
    if sync and not write_to_archive:
        print(f"{archive_posixgroup_dn} Needs written to archive OU")
        print(
            "WRITE_TO_ARCHIVE is required to make changes, please supply: -z or --write_archive"
        )
    # if sync and writing to archive permitted, perform action, add directly to archive OU
    if sync and write_to_archive:
        try:
            # notify
            print(
                f"Adding archived project {archive_posixgroup_dn} to OpenLDAP - SYNC is {sync} - WRITING TO Openldap"
            )

            # create ou
            print(f"Adding OpenLDAP project archive OU entry - DN: {archive_ou_dn}")
            add_per_project_ou_to_openldap(
                project, archive_ou_dn, archive_openldap_ou_description, write=True
            )

            # create posixgroup
            print(
                f"Adding OpenLDAP project archive posixgroup entry - DN: {archive_posixgroup_dn}"
            )
            add_project_posixgroup_to_openldap(
                archive_posixgroup_dn,
                archive_openldap_posixgroup_description,
                archive_gid,
                write=True,
            )
        except Exception as e:
            print(f"Exception adding {archive_posixgroup_dn} to OpenLDAP: {e}")


def handle_project_in_openldap_but_not_archive(
    project, project_ou_dn, archive_dn, sync=False, write_to_archive=False
):
    # if sync not permitted notify
    if not sync:
        print(
            f"{project_ou_dn} <<< WARNING WE EXPECTED THIS TO BE ARCHIVED IN OPENLDAP - PROJECT_OPENLDAP_ARCHIVE_OU is set"
        )
        print(f"{archive_dn} is the expected DN")
        print(f"Project {project.project_code} - Corrective action may be required")
    # if sync permitted but writing to archive not permitted, notify
    if sync and not write_to_archive:
        print(
            f"Project DN {project_ou_dn} needs moved to Archive OU, with DN {archive_dn} - Requires writing to archive OU"
        )
        print(
            "WRITE_TO_ARCHIVE is required to make changes, please supply: -z or --write_archive"
        )
    # if sync and writing to archive permitted, perform action, move to archive OU
    if sync and write_to_archive:
        # current_dn (ou_dn), relative_dn, ARCHIVE_OU need supplied - where relative_dn is the project's own ou
        try:
            relative_dn = construct_per_project_ou_relative_dn_str(project)
            archive_project_in_openldap(
                project_ou_dn, relative_dn, PROJECT_OPENLDAP_ARCHIVE_OU, write=True
            )
            print(
                f"Moving project to archive OU, DN: {archive_dn} in OpenLDAP - SYNC is {sync} - WRITING TO Openldap"
            )
        except Exception as e:
            print(
                f"Exception moving project {project.project_code} to archive OU, DN: {archive_dn} in OpenLDAP: {e}"
            )


def handle_project_removal_if_needed(project, project_ou_dn, sync=False):
    if project.status_id not in [
        PROJECT_STATUS_CHOICE_NEW,
        PROJECT_STATUS_CHOICE_ACTIVE,
    ]:
        # archive OU not defined, so remove this project
        if PROJECT_OPENLDAP_REMOVE_PROJECT and not PROJECT_OPENLDAP_ARCHIVE_OU:
            if not sync:
                print(
                    f"{project_ou_dn} <<< WARNING WE EXPECTED THIS TO BE REMOVED IN OPENLDAP - PROJECT_OPENLDAP_ARCHIVE_OU NOT is set"
                )
                print(
                    "Sync is required to make this change, please supply: -s or --sync"
                )
            if sync:
                try:
                    remove_project(project)
                    print(
                        f"Removed inactive project {project.project_code} from OpenLDAP - SYNC is {sync}"
                    )
                except Exception as e:
                    print(
                        f"Exception removing {project.project_code}, DN: {project_ou_dn} in OpenLDAP: {e}"
                    )


def handle_description_update(
    project,
    ldapsearch_project_result=False,
    ldapsearch_project_result_archive=False,
    project_dn="",
    archive_dn="",
    sync=False,
    write_to_archive=False,
):
    new_description = construct_project_posixgroup_description(
        project
    )  # supply project_obj

    if project.status_id in [PROJECT_STATUS_CHOICE_NEW, PROJECT_STATUS_CHOICE_ACTIVE]:
        # fetch current description from project_dn
        fetched_description = ldapsearch_get_project_description(project_dn)
        if new_description == fetched_description:
            print("Description is up-to-date.")
        if new_description != fetched_description:
            if sync:
                update_project_posixgroup_in_openldap(
                    project_dn, new_description, write=True
                )
                print(f"{new_description}")
            else:
                # line up description output
                print(f"OLD openldap_description is      {fetched_description}")
                print(f"NEW openldap_description will be {new_description}")
                print("SYNC required to update OpenLDAP description")

    if project.status_id in [PROJECT_STATUS_CHOICE_ARCHIVED]:
        # fetch current description from archive DN
        fetched_description = ldapsearch_get_project_description(archive_dn)
        if new_description == fetched_description:
            print("Description is up-to-date.")
        if new_description != fetched_description:
            if not sync:
                # line up description output
                print(f"OLD openldap_description is      {fetched_description}")
                print(f"NEW openldap_description will be {new_description}")
                print("SYNC required to update OpenLDAP description")
            if sync and not write_to_archive:
                print("CANNOT Modify descrption in OpenLDAP for this archived project")
                print(
                    "WRITE_TO_ARCHIVE is required to make changes, please supply: -z or --write_archive"
                )
            if sync and write_to_archive:
                update_project_posixgroup_in_openldap(
                    archive_dn, new_description, write=True
                )
                print(f"{new_description}")


# get active users from the coldfront django project
def local_get_cf_django_members(project_pk):
    queryset = ProjectUser.objects.filter(
        project_id=project_pk, status_id=PROJECTUSER_STATUS_CHOICE_ACTIVE
    )
    usernames = [
        user.user.username
        for user in queryset
        if user.user.username not in PROJECT_OPENLDAP_EXCLUDE_USERS
    ]
    return tuple(usernames)


def local_get_openldap_members(dn):
    entries = ldapsearch_get_project_memberuids(dn)
    members = []
    for entry in entries:
        members.extend(entry.memberUid.values)
    return tuple(members)


def sync_members(
    project,
    cf_members,
    openldap_members,
    ldapsearch_project_result=False,
    ldapsearch_project_result_archive=False,
    project_dn="",
    archive_dn="",
    sync=False,
    write_to_archive=False,
):
    if len(cf_members) == 0 and len(openldap_members) == 0:
        print(
            "NOTIFICATION: Both Coldfront django and OpenLDAP have 0 members - no action to take by sync_members"
        )
        return

    missing_in_cf = tuple(set(openldap_members) - set(cf_members))
    missing_in_openldap = tuple(set(cf_members) - set(openldap_members))

    # bail out as no valid DN
    if not ldapsearch_project_result and not ldapsearch_project_result_archive:
        print(
            "WARNING: sync_members (method) ldapsearch are both False for project OU and archive OU for project: {project.project_code}"
        )
        sys.exit(1)

    # check just single DN (valid) as expected
    if (
        ldapsearch_project_result
        and (len(project_dn) > 0)
        and not ldapsearch_project_result_archive
    ):
        member_change_dn = project_dn
    elif (
        ldapsearch_project_result_archive
        and (len(archive_dn) > 0)
        and not ldapsearch_project_result
    ):
        member_change_dn = archive_dn
    else:
        print(
            "WARNING: sync_members NO ACTION PERFORMED, couldn't match ldapsearch result and provide a valid DN"
        )
        print("DN to use for changes couldn't be set...")
        return

    if len(missing_in_cf) > 0:
        print(
            f"Users are MISSING in Coldfront (but are present in Openldap) - REMOVAL ACTION (OpenLDAP): {member_change_dn}\n {missing_in_cf}"
        )
        if not sync:
            print("sync is required to make changes, please supply: -s or --sync")
        if sync:
            if ldapsearch_project_result:
                try:
                    remove_members_from_openldap_project_posixgroup(
                        member_change_dn, missing_in_cf, write=True
                    )
                    print(f"SYNC {sync} - Removed members {missing_in_cf}")
                except Exception as e:
                    print(
                        f"Exception Removing members {missing_in_cf} in OpenLDAP DN {member_change_dn}: {e}"
                    )
            elif ldapsearch_project_result_archive:
                if not write_to_archive:
                    print(
                        "WRITE_TO_ARCHIVE is required to make changes, please supply: -z or --write_archive"
                    )
                elif write_to_archive:
                    try:
                        remove_members_from_openldap_project_posixgroup(
                            member_change_dn, missing_in_cf, write=True
                        )
                        print(f"SYNC {sync} - Removed members {missing_in_cf}")
                    except Exception as e:
                        print(
                            f"Exception Removing members {missing_in_cf} in OpenLDAP DN {member_change_dn}: {e}"
                        )

    if len(missing_in_openldap) > 0:
        print(
            f"Users are MISSING in OpenLDAP - ADDITION ACTION (OpenLDAP): {member_change_dn}\n {missing_in_openldap}"
        )
        if not sync:
            print("sync is required to make changes, please supply: -s or --sync")
        if sync:
            if ldapsearch_project_result:
                try:
                    add_members_to_openldap_project_posixgroup(
                        member_change_dn, missing_in_openldap, write=True
                    )
                    print(f"SYNC {sync} - Added members {missing_in_openldap}")
                except Exception as e:
                    print(
                        f"Exception Adding members {missing_in_openldap} in OpenLDAP DN {member_change_dn}: {e}"
                    )
            elif ldapsearch_project_result_archive:
                if not write_to_archive:
                    print(
                        "WRITE_TO_ARCHIVE is required to make changes, please supply: -z or --write_archive"
                    )
                elif write_to_archive:
                    try:
                        add_members_to_openldap_project_posixgroup(
                            member_change_dn, missing_in_openldap, write=True
                        )
                        print(f"SYNC {sync} - Added members {missing_in_openldap}")
                    except Exception as e:
                        print(
                            f"Exception Adding members {missing_in_openldap} in OpenLDAP DN {member_change_dn}: {e}"
                        )


# N.B. this is the main function to check projects...
def sync_check_project(
    project_group,
    sync=False,
    write_to_archive=False,
    update_description=False,
    skip_archived=False,
    skip_newactive=False,
):
    # 1) do some setup and checks
    project = local_get_project_by_code(project_group)
    if not project:
        return

    # skip archived projects if option supplied
    if skip_archived and project.status_id in [PROJECT_STATUS_CHOICE_ARCHIVED]:
        print("--------------------")
        print(
            f"Requested skip_archived, not processing archived project status for Project {project.project_code}"
        )
        print("")
        return

    # skip archived projects if option supplied
    if skip_newactive and project.status_id in [
        PROJECT_STATUS_CHOICE_NEW,
        PROJECT_STATUS_CHOICE_ACTIVE,
    ]:
        print("--------------------")
        print(
            f"Requested skip_newactive, not processing new or active project status for Project {project.project_code}"
        )
        print("")
        return

    # Initialise for new,active project
    project_dn = construct_dn_str(project)
    project_ou_dn = construct_ou_dn_str(project)
    # Initialise for archive project
    project_archive_dn = ""
    ldapsearch_project_result_archive = False

    if PROJECT_OPENLDAP_ARCHIVE_OU:
        project_archive_dn = construct_dn_archived_str(project)

    print("--------------------")
    print(f"processing Project {project.project_code}")
    print("")

    # does project exist in project OU
    ldapsearch_project_result = ldapsearch_check_project_dn(project_dn)
    print(f"search project OU result: {ldapsearch_project_result}")
    # does project exist in archive OU
    if PROJECT_OPENLDAP_ARCHIVE_OU:
        ldapsearch_project_result_archive = ldapsearch_check_project_dn(
            project_archive_dn
        )
        print(f"search project archive OU result: {ldapsearch_project_result_archive}")
    else:
        print(
            "search project archive OU result: N/A - PROJECT_OPENLDAP_ARCHIVE_OU is not set"
        )
        if project.status_id in [PROJECT_STATUS_CHOICE_ARCHIVED]:
            print("NOTE: This project has Coldfront status_id of Archived")
    # 1) --- END ---

    # 2) determine if the project needs added, moved or removed - ARCHIVAL
    # Use coldfront project object status id to determine what to do next... ARCHIVAL case
    # Project archived in Coldfront django
    if project.status_id in [PROJECT_STATUS_CHOICE_ARCHIVED]:
        # archive OU is setup to archive projects
        if PROJECT_OPENLDAP_ARCHIVE_OU and PROJECT_OPENLDAP_REMOVE_PROJECT:
            # project is in project OU not archive OU - DNs supplied - apart from relative, generated in function
            if ldapsearch_project_result and not ldapsearch_project_result_archive:
                handle_project_in_openldap_but_not_archive(
                    project, project_ou_dn, project_archive_dn, sync, write_to_archive
                )
                return
            # project is not in project OU, not in achive OU - supply DN to show expected DN - others generated in function
            if not ldapsearch_project_result and not ldapsearch_project_result_archive:
                handle_missing_project_in_openldap_archive(
                    project, project_dn, sync, write_to_archive
                )
                return
        # archive OU is not setup, remove project
        elif not PROJECT_OPENLDAP_ARCHIVE_OU and PROJECT_OPENLDAP_REMOVE_PROJECT:
            # project is in project OU, needs removed, use project's ou_dn - supplied - only this is needed here
            if ldapsearch_project_result:
                handle_project_removal_if_needed(project, project_ou_dn, sync)
                return

        # state should be correct, report as archived
        if PROJECT_OPENLDAP_ARCHIVE_OU:
            if ldapsearch_project_result_archive:
                print(
                    f"Project {project.project_code} is an archived project - found {project_archive_dn}"
                )

    # 2 continued...) determine if the project needs added - NEW or ACTIVE
    # Use coldfront project object status id to determine what to do next... NEW or ACTIVE case
    # Project is new or active status in Coldfront django
    elif project.status_id in [PROJECT_STATUS_CHOICE_NEW, PROJECT_STATUS_CHOICE_ACTIVE]:
        if not ldapsearch_project_result:
            handle_missing_project_in_openldap_new_active(project, sync)
            return
        else:
            print(
                f"Project {project.project_code} is a new or active project - found {project_dn}"
            )
    else:
        # project status choice wasnt matched
        print("ERROR: Unrecognised project status - HALTING")
        sys.exit(1)
    # 2) --- END ---

    # 3) Fetch members and determine DN through ldapsearch
    # Get the Coldfront django members
    cf_members = local_get_cf_django_members(project.pk)

    # Initialise openldap_members to None to avoid issue where archive OU was originally present, then disabled
    # To search for an archive DN, we'd have to pass the PROJECT_OPENLDAP_ARCHIVE_OU
    openldap_members = None
    # OpenLDAP membership check requires directing to the right OU and DN
    if ldapsearch_project_result:
        openldap_members = local_get_openldap_members(project_dn)
    if PROJECT_OPENLDAP_ARCHIVE_OU:
        if ldapsearch_project_result_archive:
            openldap_members = local_get_openldap_members(project_archive_dn)
    # 3) --- END ---

    # 4) Membership checking and syncing
    # if members weren't found in searches then they either shouldn't be (as expected OR archived previously and now PROJECT_OPENLDAP_ARCHIVE_OU is unset), bail out for this project
    if openldap_members is None:
        print(
            "NOTIFICATION: openldap_members could not be determined ('None' value), possible causes include:"
        )
        print(
            "- project has been removed from OpenLDAP - as expected - archive OU is not set"
        )
        print("- archived project in Coldfront no further action required...")
        print(
            "- previously enabling OpenLDAP archive OU, then disabling, whilst having projects in the archive OU"
        )
        return

    # if there are 0 OpenLDAP members notify, also notify if there are coldfront django members
    if len(openldap_members) == 0:
        print(
            f"NOTIFICATION: There are {len(cf_members)} Coldfront (django) project members which could be added to OpenLDAP for this project"
        )
        if len(cf_members) > 0:
            print(f"{cf_members}")

    # always try a sync_members
    sync_members(
        project,
        cf_members,
        openldap_members,
        ldapsearch_project_result,
        ldapsearch_project_result_archive,
        project_dn,
        project_archive_dn,
        sync,
        write_to_archive,
    )
    # 4) --- END ---

    # 5) If sought update the OpenLDAP description for the project
    # finally update the OpenLDAP description if requested, will not check, will update regardless
    if update_description:
        handle_description_update(
            project,
            ldapsearch_project_result,
            ldapsearch_project_result_archive,
            project_dn,
            project_archive_dn,
            sync,
            write_to_archive,
        )
    # 5) -- END ---


""" Main loop to loop every Coldfront django project pk """


def loop_all_projects(
    sync=False,
    write_to_archive=False,
    update_description=False,
    skip_archived=False,
    skip_newactive=False,
):
    projects = Project.objects.filter(
        status_id__in=[
            PROJECT_STATUS_CHOICE_NEW,
            PROJECT_STATUS_CHOICE_ACTIVE,
            PROJECT_STATUS_CHOICE_ARCHIVED,
        ]
    ).order_by("id")

    if len(projects) == 0:
        print("No projects found by loop_all_projects - EXITING")
        return

    for project in projects:
        if hasattr(project, "project_code") and project.project_code:
            project_code = project.project_code
            sync_check_project(
                project_code,
                sync,
                write_to_archive,
                update_description,
                skip_archived,
                skip_newactive,
            )
        else:
            # won't continue to process so print seperator here
            print("--------------------")
            print(
                f"Project with pk in Coldfront django {project.pk} - has no project_code"
            )
            print("NOT PROCESSING!")

    return True


class Command(BaseCommand):
    help = "Sync projects and memberUids in OpenLDAP (from Coldfront)"

    def add_arguments(self, parser):
        parser.add_argument(
            "-a",
            "--all",
            help="Check all OpenLDAP projects against Coldfront-django",
            action="store_true",
        )
        parser.add_argument(
            "-p",
            "--project_group",
            help="Check specific group in OpenLDAP against Coldfront-django",
        )
        parser.add_argument(
            "-s", "--sync", help="Sync changes to OpenLDAP", action="store_true"
        )
        parser.add_argument(
            "-z",
            "--write_archive",
            help="Enable writing to the OpenLDAP archive OU",
            action="store_true",
        )
        parser.add_argument(
            "-d",
            "--update_description",
            help="Update project description in OpenLDAP (which includes title)",
            action="store_true",
        )
        parser.add_argument(
            "-x",
            "--skip_archived",
            help="Skip projects with archived status in Coldfront",
            action="store_true",
        )
        parser.add_argument(
            "-e",
            "--skip_newactive",
            help="Skip projects with New or Active status in Coldfront",
            action="store_true",
        )

    def handle(self, *args, **options):
        verbosity = int(options["verbosity"])
        root_logger = logging.getLogger("")
        if verbosity == 0:
            root_logger.setLevel(logging.ERROR)
        elif verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.WARN)

        self.sync = False
        if options["sync"]:
            self.sync = True
            logger.warning("Enabling writes - Syncing OpenLDAP with ColdFront")

        self.write_archive = False
        if options["write_archive"]:
            self.write_archive = True
            self.write_archive = options["write_archive"]

        self.update_description = False
        if options["update_description"]:
            self.update_description = True
            self.update_description = options["update_description"]

        self.skip_archived = False
        if options["skip_archived"]:
            self.skip_archived = True
            self.skip_archived = options["skip_archived"]

        self.skip_newactive = False
        if options["skip_newactive"]:
            self.skip_newactive = True
            self.skip_newactive = options["skip_newactive"]

        self.filter_group = ""
        if options["project_group"]:
            logger.info(
                "Filtering output by project_group: %s", options["project_group"]
            )
            self.filter_group = options["project_group"]

        self.all = False
        if options["all"]:
            self.all = True
            logger.warning("Syncing ALL OpenLDAP groups with ColdFront")

        if self.filter_group:
            sync_check_project(
                self.filter_group,
                self.sync,
                self.write_archive,
                self.update_description,
                self.skip_archived,
                self.skip_newactive,
            )

        if self.all:
            loop_all_projects(
                self.sync,
                self.write_archive,
                self.update_description,
                self.skip_archived,
                self.skip_newactive,
            )

        if not self.filter_group and not self.all:
            print("")
            print(
                "No action taken - no option was supplied for a specific project_group in OpenLDAP (-p) or to check all groups in OpenLDAP (-a)"
            )
            print("")
