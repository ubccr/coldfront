# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime
import logging
import os
import re
import sys

from coldfront.core.resource.models import Resource
from coldfront.plugins.slurm.utils import (
    SLURM_ACCOUNT_ATTRIBUTE_NAME,
    SLURM_CLUSTER_ATTRIBUTE_NAME,
    SLURM_SPECS_ATTRIBUTE_NAME,
    SLURM_USER_SPECS_ATTRIBUTE_NAME,
    SlurmError,
)

logger = logging.getLogger(__name__)


class SlurmParserError(SlurmError):
    pass


class SlurmBase:
    def __init__(self, name, specs=None):
        if specs is None:
            specs = []

        self.name = name
        self.specs = specs

    def spec_list(self):
        """Return unique list of Slurm Specs"""
        items = []
        for s in self.specs:
            for i in s.split(":"):
                items.append(i)

        return list(set(items))

    def format_specs(self):
        """Format unique list of Slurm Specs"""
        items = []
        for s in self.specs:
            for i in s.split(":"):
                items.append(i)

        return ":".join([x for x in self.spec_list()])

    def _write(self, out, data):
        try:
            out.write(data)
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)


class SlurmCluster(SlurmBase):
    def __init__(self, name, specs=None):
        super().__init__(name, specs=specs)
        self.accounts = {}

    @staticmethod
    def new_from_stream(stream):
        """Create a new SlurmCluster by parsing the output from sacctmgr dump."""
        cluster = None
        parent = None
        for line in stream:
            line = line.strip()
            if re.match("^#", line):
                continue
            elif re.match("^Cluster - '[^']+'", line):
                parts = line.split(":")
                name = re.sub(r"^Cluster - ", "", parts[0]).strip("\n'")
                if len(name) == 0:
                    raise (SlurmParserError(f"Cluster name not found for line: {line}"))
                cluster = SlurmCluster(name)
                cluster.specs += parts[1:]
            elif re.match("^Account - '[^']+'", line):
                account = SlurmAccount.new_from_sacctmgr(line)
                cluster.accounts[account.name] = account
            elif re.match("^Parent - '[^']+'", line):
                parent = re.sub(r"^Parent - ", "", line).strip("\n'")
                if parent == "root":
                    cluster.accounts["root"] = SlurmAccount("root")
                if not parent:
                    raise (SlurmParserError(f"Parent name not found for line: {line}"))
            elif re.match("^User - '[^']+'", line):
                user = SlurmUser.new_from_sacctmgr(line)
                if not parent:
                    raise (SlurmParserError(f"Found user record without Parent for line: {line}"))
                account = cluster.accounts[parent]
                account.add_user(user)
                cluster.accounts[parent] = account

        if not cluster or not cluster.name:
            raise (SlurmParserError("Failed to parse Slurm cluster name. Is this in sacctmgr dump file format?"))

        return cluster

    @staticmethod
    def new_from_resource(resource):
        """Create a new SlurmCluster from a ColdFront Resource model."""
        name = resource.get_attribute(SLURM_CLUSTER_ATTRIBUTE_NAME)
        specs = resource.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)
        user_specs = resource.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
        if not name:
            raise (SlurmError(f"Resource {resource} missing slurm_cluster"))

        cluster = SlurmCluster(name, specs)

        # Process allocations
        for allocation in resource.allocation_set.filter(status__name__in=["Active", "Renewal Requested"]):
            cluster.add_allocation(allocation, user_specs=user_specs)

        # Process child resources
        children = Resource.objects.filter(parent_resource_id=resource.id, resource_type__name="Cluster Partition")
        for r in children:
            partition_specs = r.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)
            partition_user_specs = r.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
            for allocation in r.allocation_set.filter(status__name__in=["Active", "Renewal Requested"]):
                cluster.add_allocation(allocation, specs=partition_specs, user_specs=partition_user_specs)

        return cluster

    def add_allocation(self, allocation, specs=None, user_specs=None):
        if specs is None:
            specs = []

        """Add accounts from a ColdFront Allocation model to SlurmCluster"""
        name = allocation.get_attribute(SLURM_ACCOUNT_ATTRIBUTE_NAME)
        if not name:
            name = "root"

        logger.debug("Adding allocation name=%s specs=%s user_specs=%s", name, specs, user_specs)
        account = self.accounts.get(name, SlurmAccount(name))
        account.add_allocation(allocation, user_specs=user_specs)
        account.specs += specs
        self.accounts[name] = account

    def write(self, out):
        self._write(out, f"# ColdFront Allocation Slurm associations dump {datetime.datetime.now().date()}\n")
        self._write(
            out,
            f"Cluster - '{self.name}':{self.format_specs()}\n",
        )
        if "root" in self.accounts:
            self.accounts["root"].write(out)
        else:
            self._write(out, "Parent - 'root'\n")
            self._write(out, "User - 'root':DefaultAccount='root':AdminLevel='Administrator':Fairshare=1\n")

        for name, account in self.accounts.items():
            if account.name == "root":
                continue
            account.write(out)

        for name, account in self.accounts.items():
            account.write_users(out)


class SlurmAccount(SlurmBase):
    def __init__(self, name, specs=None):
        super().__init__(name, specs=specs)
        self.users = {}

    @staticmethod
    def new_from_sacctmgr(line):
        """Create a new SlurmAccount by parsing a line from sacctmgr dump. For
        example: Account - 'physics':Description='physics group':Organization='cas':Fairshare=100"""
        if not re.match("^Account - '[^']+'", line):
            raise (SlurmParserError(f'Invalid format. Must start with "Account" for line: {line}'))

        parts = line.split(":")
        name = re.sub(r"^Account - ", "", parts[0]).strip("\n'")
        if len(name) == 0:
            raise (SlurmParserError(f"Cluster name not found for line: {line}"))

        return SlurmAccount(name, specs=parts[1:])

    def add_allocation(self, allocation, user_specs=None):
        """Add users from a ColdFront Allocation model to SlurmAccount"""
        if user_specs is None:
            user_specs = []

        name = allocation.get_attribute(SLURM_ACCOUNT_ATTRIBUTE_NAME)
        if not name:
            name = "root"

        if name != self.name:
            raise (SlurmError(f"Allocation {allocation} slurm_account_name does not match {self.name}"))

        self.specs += allocation.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)

        allocation_user_specs = allocation.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
        for u in allocation.allocationuser_set.filter(status__name="Active"):
            user = SlurmUser(u.user.username)
            user.specs += allocation_user_specs
            user.specs += user_specs
            self.add_user(user)

    def add_user(self, user):
        if user.name not in self.users:
            self.users[user.name] = user

        rec = self.users[user.name]
        rec.specs += user.specs
        self.users[user.name] = rec

    def write(self, out):
        if self.name != "root":
            self._write(
                out,
                f"Account - '{self.name}':{self.format_specs()}\n",
            )

    def write_users(self, out):
        self._write(out, f"Parent - '{self.name}'\n")
        for uid, user in self.users.items():
            user.write(out)


class SlurmUser(SlurmBase):
    @staticmethod
    def new_from_sacctmgr(line):
        """Create a new SlurmUser by parsing a line from sacctmgr dump. For
        example: User - 'jane':DefaultAccount='physics':Fairshare=Parent:QOS='general-compute'"""
        if not re.match("^User - '[^']+'", line):
            raise (SlurmParserError(f'Invalid format. Must start with "User" for line: {line}'))

        parts = line.split(":")
        name = re.sub(r"^User - ", "", parts[0]).strip("\n'")
        if len(name) == 0:
            raise (SlurmParserError(f"User name not found for line: {line}"))

        return SlurmUser(name, specs=parts[1:])

    def write(self, out):
        self._write(
            out,
            f"User - '{self.name}':{self.format_specs()}\n",
        )
