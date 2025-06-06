# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import warnings
import sys
import logging
from ldap3.core.exceptions import LDAPException

from coldfront.core.utils.common import import_from_settings

from coldfront.plugins.project_openldap.utils import (
    PROJECT_OPENLDAP_BIND_USER,
    ldapsearch_check_project_ou,
)

from django.core.management.base import BaseCommand

""" Coldfront project_openldap plugin - django management command -  project_openldap_check_setup.py """

# Example pre-reqs - we require project_code
# --------------------------------------
# i. (required) PROJECT_CODE="CDF"
# ii. (required) PROJECT_CODE_PADDING=4
# --------------------------------------
# See plugin directory README.md for explanation of project_openldap plugin variables
# --------------------------------------


def check_env_var_existance(name, expected_value, required=True):
    print("\033[36m---------------------------------------------------\033[0m")
    print(f"\033[36m Checking pre-requisite environment variable, {name}... \033[0m")
    print("\033[36m---------------------------------------------------\033[0m")

    try:
        env_var = import_from_settings(name, expected_value)

        if not env_var and not required:
            print(f"\033[33m [OPTIONAL] {name} is not set (using default)\033[0m")
            return None
        if not env_var and required:
            print(
                f"\033[31m [REQUIRED] WARNING - {name} is not set or 0 length in settings!\033[0m"
            )
            return None

        if name == "PROJECT_CODE_PADDING" and int(env_var) == 0:
            print(
                "\033[31m [OPTIONAL] WARNING PROJECT_CODE_PADDING is NOT VALID - example value: 4!\033[0m"
            )
            return None
        if name == "PROJECT_OPENLDAP_GID_START" and int(env_var) <= 1000:
            print(
                f"\033[31m [REQUIRED] WARNING PROJECT_OPENLDAP_GID_START should be > 1000!, currently is {env_var}\033[0m"
            )
            print("\033[31mADVISORY - FIX THIS ERROR FIRST!\033[0m")
            return None

        if name == "PROJECT_OPENLDAP_DESCRIPTION_TITLE_LENGTH" and (
            int(env_var) <= 10 or int(env_var) >= 300
        ):
            print(
                "\033[31m [REQUIRED] WARNING PROJECT_OPENLDAP_DESCRIPTION_TITLE_LENGTH should be lesser then 300 but more than 10! \033[0m"
            )
            return None

        status = "[REQUIRED]" if required else "[OPTIONAL]"
        print(
            f"\033[32m{status} OK - {name} is {env_var if 'PASSWORD' not in name else 'set'}\033[0m"
        )
    except ImportError:
        warnings.warn(f"Failed to import {name}", ImportWarning)


def check_all_openldap_options_enabled():
    print("")
    print("\033[36m---------------------------------------------------\033[0m")
    print(
        "\033[36m Check if all of required Project OpenLDAP imports are loaded in the configuration file. \033[0m"
    )
    print("\033[36m---------------------------------------------------\033[0m")
    print("")

    required_vars = {
        "PROJECT_CODE": True,  # pre-req
        "PROJECT_CODE_PADDING": True,  # pre-req
        "PLUGIN_PROJECT_OPENLDAP": True,  # to-enable-plugin
        "PROJECT_OPENLDAP_GID_START": True,
        "PROJECT_OPENLDAP_SERVER_URI": True,
        "PROJECT_OPENLDAP_OU": True,
        "PROJECT_OPENLDAP_BIND_USER": True,
        "PROJECT_OPENLDAP_BIND_PASSWORD": True,
        "PROJECT_OPENLDAP_REMOVE_PROJECT": True,
        "PROJECT_OPENLDAP_DESCRIPTION_TITLE_LENGTH": True,
    }

    optional_vars = {
        "PROJECT_OPENLDAP_ARCHIVE_OU": None,
        "PROJECT_OPENLDAP_CONNECT_TIMEOUT": True,
        "PROJECT_OPENLDAP_USE_SSL": True,
        "PROJECT_OPENLDAP_USE_TLS": False,
        "PROJECT_OPENLDAP_PRIV_KEY_FILE": None,
        "PROJECT_OPENLDAP_CERT_FILE": None,
        "PROJECT_OPENLDAP_CACERT_FILE": None,
    }

    # Check required vars
    for key, value in required_vars.items():
        check_env_var_existance(key, value, required=True)

    # Check optional vars
    for key, value in optional_vars.items():
        check_env_var_existance(key, value, required=False)


def check_setup_ldapsearch():
    print("")
    print("\033[36m---------------------------------------------------\033[0m")
    print("\033[36m Test ldapsearch  \033[0m")
    print("\033[36m---------------------------------------------------\033[0m")
    print("")

    # 1. Search for the REQUIRED project OU
    # 2. Check and search for the OPTIONAL archive_project OU

    PROJECT_OPENLDAP_OU = import_from_settings("PROJECT_OPENLDAP_OU", True)
    PROJECT_OPENLDAP_ARCHIVE_OU = import_from_settings(
        "PROJECT_OPENLDAP_ARCHIVE_OU", True
    )

    print("\033[36m---------------------------------------------------\033[0m")

    if PROJECT_OPENLDAP_OU:
        print("\033[36m LDAP SEARCH  \033[0m")
        print(f"{PROJECT_OPENLDAP_OU} is set to {PROJECT_OPENLDAP_OU}")
        print("ldapsearch...")
        try:
            ldapsearch_check_project_ou_result = ldapsearch_check_project_ou(
                PROJECT_OPENLDAP_OU
            )
            if ldapsearch_check_project_ou_result and not isinstance(
                ldapsearch_check_project_ou_result, Exception
            ):
                print(
                    f"\033[32mSUCCESS ldapsearch can find {PROJECT_OPENLDAP_OU}: {ldapsearch_check_project_ou_result} using bind user {PROJECT_OPENLDAP_BIND_USER}\033[0m"
                )
            else:
                print(
                    f"\033[31mFAILURE ldapsearch CANT find {PROJECT_OPENLDAP_OU}: {ldapsearch_check_project_ou_result} using bind user {PROJECT_OPENLDAP_BIND_USER}\033[0m"
                )
        except LDAPException:
            print(f"ERROR WITH LDAPSEARCH: {LDAPException}")

    print("\033[36m---------------------------------------------------\033[0m")

    # Perform the search
    if PROJECT_OPENLDAP_ARCHIVE_OU:
        print("\033[36m LDAP ARCHIVE SEARCH  \033[0m")
        print(f"{PROJECT_OPENLDAP_ARCHIVE_OU} is set to {PROJECT_OPENLDAP_ARCHIVE_OU}")
        print("ldapsearch...")
        try:
            ldapsearch_check_project_ou_result = ldapsearch_check_project_ou(
                PROJECT_OPENLDAP_ARCHIVE_OU
            )
            if ldapsearch_check_project_ou_result and not isinstance(
                ldapsearch_check_project_ou_result, Exception
            ):
                print(
                    f"\033[32mSUCCESS ldapsearch can find {PROJECT_OPENLDAP_ARCHIVE_OU}: {ldapsearch_check_project_ou_result} using bind user {PROJECT_OPENLDAP_BIND_USER}\033[0m"
                )
            else:
                print(
                    f"\033[31mFAILURE ldapsearch CANT find {PROJECT_OPENLDAP_ARCHIVE_OU}: {ldapsearch_check_project_ou_result} using bind user {PROJECT_OPENLDAP_BIND_USER}\033[0m"
                )
        except LDAPException:
            print(f"ERROR WITH LDAPSEARCH: {LDAPException}")

    print("\033[36m---------------------------------------------------\033[0m")


class Command(BaseCommand):
    help = "Check settings for project_openldap plugin"

    def add_arguments(self, parser):
        parser.add_argument(
            "-a",
            "--all",
            help="Check both imports and ldapsearch work",
            action="store_true",
        )
        parser.add_argument(
            "-i",
            "--imports",
            help="Check all imports for the plugin",
            action="store_true",
        )
        parser.add_argument(
            "-l", "--ldapsearch", help="Check search to OpenLDAP", action="store_true"
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

        self.all = False
        if options["all"]:
            self.imports = True
            check_all_openldap_options_enabled()
            check_setup_ldapsearch()
            sys.exit(0)

        self.imports = False
        if options["imports"]:
            self.imports = True
            check_all_openldap_options_enabled()
            sys.exit(0)

        self.ldapsearch = False
        if options["ldapsearch"]:
            self.ldapsearch = True
            check_setup_ldapsearch()
            sys.exit(0)

        if not self.all and not self.imports and not self.ldapsearch:
            print(
                "\n No action taken - no option was supplied -i (--imports), -l (ldapsearch) or -a (--all)"
            )
