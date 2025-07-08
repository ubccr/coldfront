# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import sys
import tempfile

from django.core.management.base import BaseCommand

from coldfront.core.resource.models import ResourceAttribute
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.slurm.associations import SlurmCluster
from coldfront.plugins.slurm.utils import (
    SLURM_CLUSTER_ATTRIBUTE_NAME,
    SlurmError,
    slurm_dump_cluster,
    slurm_remove_account,
    slurm_remove_assoc,
    slurm_remove_qos,
)

SLURM_IGNORE_USERS = import_from_settings("SLURM_IGNORE_USERS", [])
SLURM_IGNORE_ACCOUNTS = import_from_settings("SLURM_IGNORE_ACCOUNTS", [])
SLURM_IGNORE_CLUSTERS = import_from_settings("SLURM_IGNORE_CLUSTERS", [])
SLURM_NOOP = import_from_settings("SLURM_NOOP", False)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check consistency between Slurm associations and ColdFront allocations"

    def add_arguments(self, parser):
        parser.add_argument("-i", "--input", help="Path to sacctmgr dump flat file as input. Defaults to stdin")
        parser.add_argument("-c", "--cluster", help="Run sacctmgr dump [cluster] as input")
        parser.add_argument(
            "-s", "--sync", help="Remove associations in Slurm that no longer exist in ColdFront", action="store_true"
        )
        parser.add_argument("-n", "--noop", help="Print commands only. Do not run any commands.", action="store_true")
        parser.add_argument("-u", "--username", help="Check specific username")
        parser.add_argument("-a", "--account", help="Check specific account")
        parser.add_argument("-x", "--header", help="Include header in output", action="store_true")

    def write(self, data):
        try:
            self.stdout.write(data)
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)

    def _skip_user(self, user, account):
        if user in SLURM_IGNORE_USERS:
            logger.debug("Ignoring user %s", user)
            return True

        if account in SLURM_IGNORE_ACCOUNTS:
            logger.debug("Ignoring account %s", account)
            return True

        if self.filter_account and account != self.filter_account:
            return True

        if self.filter_user and user != self.filter_user:
            return True

        return False

    def _skip_account(self, account):
        if account in SLURM_IGNORE_ACCOUNTS:
            logger.debug("Ignoring account %s", account)
            return True

        if self.filter_user:
            return True

        if self.filter_account and account != self.filter_account:
            return True

        return False

    def remove_user(self, user, account, cluster):
        if self._skip_user(user, account):
            return

        if self.sync:
            try:
                slurm_remove_assoc(user, cluster, account, noop=self.noop)
            except SlurmError as e:
                logger.error(
                    "Failed removing Slurm association user %s account %s cluster %s: %s", user, account, cluster, e
                )
            else:
                logger.error(
                    "Removed Slurm association user %s account %s cluster %s successfully", user, account, cluster
                )

        row = [
            user,
            account,
            cluster,
            "Remove",
        ]

        self.write("\t".join(row))

    def remove_account(self, account, cluster):
        if self._skip_account(account):
            return

        if self.sync:
            try:
                slurm_remove_account(cluster, account, noop=self.noop)
            except SlurmError as e:
                logger.error("Failed removing Slurm account %s cluster %s: %s", account, cluster, e)
            else:
                logger.error("Removed Slurm account %s cluster %s successfully", account, cluster)

        row = [
            "",
            account,
            cluster,
            "Remove",
        ]

        self.write("\t".join(row))

    def remove_qos(self, user, account, cluster, qos):
        if self._skip_user(user, account):
            return

        if self.sync:
            try:
                slurm_remove_qos(user, cluster, account, qos, noop=self.noop)
                pass
            except SlurmError as e:
                logger.error(
                    "Failed removing Slurm qos %s for user %s account %s cluster %s: %s", qos, user, account, cluster, e
                )
            else:
                logger.error(
                    "Removed Slurm qos %s for user %s account %s cluster %s successfully", qos, user, account, cluster
                )

        row = [user, account, cluster, "Remove", qos]

        self.write("\t".join(row))

    def _parse_qos(self, qos):
        if qos.startswith("QOS+="):
            qos = qos.replace("QOS+=", "")
            qos = qos.replace("'", "")
            return qos.split(",")
        elif qos.startswith("QOS="):
            qos = qos.replace("QOS=", "")
            qos = qos.replace("'", "")
            lst = []
            for q in qos.split(","):
                if q.startswith("+"):
                    lst.append(q.replace("+", ""))
            return lst

        return []

    def _diff_qos(self, account_name, cluster_name, user_a, user_b):
        logger.debug(
            "diff qos: cluster=%s account=%s uid=%s a=%s b=%s",
            cluster_name,
            account_name,
            user_a.name,
            user_a.spec_list(),
            user_b.spec_list(),
        )

        specs_a = []
        for s in user_a.spec_list():
            if s.startswith("QOS"):
                specs_a += self._parse_qos(s)

        specs_b = []
        for s in user_b.spec_list():
            if s.startswith("QOS"):
                specs_b += self._parse_qos(s)

        specs_set_a = set(specs_a)
        specs_set_b = set(specs_b)

        diff = specs_set_a.difference(specs_set_b)
        logger.debug(
            "diff qos: cluster=%s account=%s uid=%s a=%s b=%s diff=%s",
            cluster_name,
            account_name,
            user_a.name,
            specs_set_a,
            specs_set_b,
            diff,
        )

        if len(diff) > 0:
            self.remove_qos(user_a.name, account_name, cluster_name, "QOS-=" + ",".join([x for x in list(diff)]))

    def _diff(self, cluster_a, cluster_b):
        for name, account in cluster_a.accounts.items():
            if name == "root":
                continue

            if name in cluster_b.accounts:
                total = 0
                for uid, user in account.users.items():
                    if uid == "root":
                        continue
                    if uid not in cluster_b.accounts[name].users:
                        self.remove_user(uid, name, cluster_a.name)
                        total += 1
                    else:
                        self._diff_qos(name, cluster_a.name, user, cluster_b.accounts[name].users[uid])

                if total == len(account.users):
                    self.remove_account(name, cluster_a.name)
            else:
                for uid, user in account.users.items():
                    self.remove_user(uid, name, cluster_a.name)

                self.remove_account(name, cluster_a.name)

    def check_consistency(self, slurm_cluster, coldfront_cluster):
        # Check for accounts in Slurm NOT in ColdFront
        self._diff(slurm_cluster, coldfront_cluster)

    def _cluster_from_dump(self, cluster):
        slurm_cluster = None
        with tempfile.TemporaryDirectory() as tmpdir:
            fname = os.path.join(tmpdir, "cluster.cfg")
            try:
                slurm_dump_cluster(cluster, fname)
                with open(fname) as fh:
                    slurm_cluster = SlurmCluster.new_from_stream(fh)
            except SlurmError as e:
                logger.error("Failed to dump Slurm cluster %s: %s", cluster, e)

        return slurm_cluster

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
            root_logger.setLevel(logging.WARNING)

        self.sync = False
        if options["sync"]:
            self.sync = True
            logger.warning("Syncing Slurm with ColdFront")

        self.noop = SLURM_NOOP
        if options["noop"]:
            self.noop = True
            logger.warning("NOOP enabled")

        if options["cluster"]:
            slurm_cluster = self._cluster_from_dump(options["cluster"])
        elif options["input"]:
            with open(options["input"]) as fh:
                slurm_cluster = SlurmCluster.new_from_stream(fh)
        else:
            slurm_cluster = SlurmCluster.new_from_stream(sys.stdin)

        if not slurm_cluster:
            logger.error("Failed to import existing Slurm associations")
            sys.exit(1)

        if slurm_cluster.name in SLURM_IGNORE_CLUSTERS:
            logger.warning("Ignoring cluster %s. Nothing to do.", slurm_cluster.name)
            sys.exit(0)

        try:
            resource = ResourceAttribute.objects.get(
                resource_attribute_type__name=SLURM_CLUSTER_ATTRIBUTE_NAME, value=slurm_cluster.name
            ).resource
        except ResourceAttribute.DoesNotExist:
            logger.error(
                "No Slurm '%s' cluster resource found in ColdFront using '%s' attribute",
                slurm_cluster.name,
                SLURM_CLUSTER_ATTRIBUTE_NAME,
            )
            sys.exit(1)

        header = [
            "username",
            "account",
            "cluster",
            "slurm_action",
            "slurm_specs",
        ]

        if options["header"]:
            self.write("\t".join(header))

        self.filter_user = options["username"]
        self.filter_account = options["account"]

        coldfront_cluster = SlurmCluster.new_from_resource(resource)

        self.check_consistency(slurm_cluster, coldfront_cluster)
