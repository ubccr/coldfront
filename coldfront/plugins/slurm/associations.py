# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime
import logging
import os
import re
import sys

from django.core.exceptions import ObjectDoesNotExist

from coldfront.core.allocation.models import Allocation, AllocationAttribute, AllocationAttributeType
from coldfront.core.resource.models import Resource
from coldfront.plugins.slurm.utils import (
    SLURM_ACCOUNT_ATTRIBUTE_NAME,
    SLURM_CHILDREN_ATTRIBUTE_NAME,
    SLURM_CLUSTER_ATTRIBUTE_NAME,
    SLURM_SPECS_ATTRIBUTE_NAME,
    SLURM_USER_SPECS_ATTRIBUTE_NAME,
    SlurmError,
)

SLURM_ACCOUNT_ATTRIBUTE_TYPE = AllocationAttributeType.objects.get(name=SLURM_ACCOUNT_ATTRIBUTE_NAME)

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
        parent_account = None
        no_cluster_error = SlurmParserError("Failed to parse Slurm cluster name. Is this in sacctmgr dump file format?")
        for line in stream:
            line = line.strip()
            if re.match("^#", line):
                continue
            elif re.match("^Cluster - '[^']+'", line):
                parts = line.split(":")
                name = re.sub(r"^Cluster - ", "", parts[0]).strip("\n'")
                if len(name) == 0:
                    raise SlurmParserError(f"Cluster name not found for line: {line}")
                cluster = SlurmCluster(name)
                cluster.specs += parts[1:]
            elif re.match("^Account - '[^']+'", line):
                if not cluster or not cluster.name:
                    raise no_cluster_error
                account = SlurmAccount.new_from_sacctmgr(line)
                if parent == "root":
                    cluster.accounts[account.name] = account
                elif parent_account:
                    parent_account.add_child(account)
            elif re.match("^Parent - '[^']+'", line):
                if not cluster or not cluster.name:
                    raise no_cluster_error
                parent = re.sub(r"^Parent - ", "", line).strip("\n'")
                if parent == "root":
                    cluster.accounts["root"] = SlurmAccount("root")
                if not parent:
                    raise SlurmParserError(f"Parent name not found for line: {line}")
                parent_account = cluster.get_account(parent)
            elif re.match("^User - '[^']+'", line):
                if not cluster or not cluster.name:
                    raise no_cluster_error
                user = SlurmUser.new_from_sacctmgr(line)
                if not parent or not parent_account:
                    raise SlurmParserError(f"Found user record without Parent for line: {line}")
                parent_account.add_child(user)

        if not cluster or not cluster.name:
            raise no_cluster_error

        return cluster

    @staticmethod
    def new_from_resource(resource):
        """Create a new SlurmCluster from a ColdFront Resource model."""
        name = resource.get_attribute(SLURM_CLUSTER_ATTRIBUTE_NAME)
        specs = resource.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)
        user_specs = resource.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
        if not name:
            raise SlurmError(f"Resource {resource} missing slurm_cluster")

        cluster = SlurmCluster(name, specs)

        # Process allocations
        allocations = resource.allocation_set.filter(status__name__in=["Active", "Renewal Requested"])
        for allocation in allocations:
            cluster.add_allocation(allocation, allocations, user_specs=user_specs)
        # remove child accounts cluster accounts
        child_accounts = set()
        for account in cluster.accounts.values():
            if account.child_type == SlurmAccount:
                child_accounts.update(account.children.keys())
        for account_name in child_accounts:
            del cluster.accounts[account_name]

        # Process child resources
        children = Resource.objects.filter(parent_resource_id=resource.id, resource_type__name="Cluster Partition")
        for r in children:
            partition_specs = r.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)
            partition_user_specs = r.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
            allocations = r.allocation_set.filter(status__name__in=["Active", "Renewal Requested"])
            for allocation in allocations:
                cluster.add_allocation(allocation, allocations, specs=partition_specs, user_specs=partition_user_specs)
            # remove child accounts cluster accounts
            child_accounts = set()
            for account in cluster.accounts.values():
                if account.child_type == SlurmAccount:
                    child_accounts.update(account.children.keys())
            for account_name in child_accounts:
                del cluster.accounts[account_name]

        return cluster

    def add_allocation(self, allocation, res_allocations, specs=None, user_specs=None):
        if specs is None:
            specs = []

        """Add accounts from a ColdFront Allocation model to SlurmCluster"""
        name = allocation.get_attribute(SLURM_ACCOUNT_ATTRIBUTE_NAME)
        if not name:
            name = "root"

        logger.debug("Adding allocation name=%s specs=%s user_specs=%s", name, specs, user_specs)
        account = self.accounts.get(name, SlurmAccount(name))
        account.add_allocation(allocation, res_allocations, user_specs=user_specs)
        account.specs += specs
        self.accounts[name] = account

    def get_account(self, account_name):
        if account_name in self.accounts.keys():
            return self.accounts[account_name]
        for account in self.accounts.values():
            result = account.get_account(account_name)
            if result:
                return result
        return None

    def write(self, out):
        self._write(out, f"# ColdFront Allocation Slurm associations dump {datetime.datetime.now().date()}\n")
        self._write(out, f"Cluster - '{self.name}':{self.format_specs()}\n")
        if "root" in self.accounts:
            self.accounts["root"].write(out)
        else:
            self._write(out, "Parent - 'root'\n")
            self._write(out, "User - 'root':DefaultAccount='root':AdminLevel='Administrator':Fairshare=1\n")

        for account in self.accounts.values():
            if account.name == "root":
                continue
            account.write(out)

        for name, account in self.accounts.items():
            account.write_children(out)


class SlurmAccount(SlurmBase):
    def __init__(self, name, specs=None):
        super().__init__(name, specs=specs)
        self.child_type = None
        self.children = {}

    @staticmethod
    def new_from_sacctmgr(line):
        """Create a new SlurmAccount by parsing a line from sacctmgr dump. For
        example: Account - 'physics':Description='physics group':Organization='cas':Fairshare=100"""
        if not re.match("^Account - '[^']+'", line):
            raise SlurmParserError(f'Invalid format. Must start with "Account" for line: {line}')

        parts = line.split(":")
        name = re.sub(r"^Account - ", "", parts[0]).strip("\n'")
        if len(name) == 0:
            raise SlurmParserError(f"Cluster name not found for line: {line}")

        return SlurmAccount(name, specs=parts[1:])

    def add_allocation(self, allocation: Allocation, res_allocations, user_specs=None):
        """Add users from a ColdFront Allocation model to SlurmAccount"""
        if user_specs is None:
            user_specs = []

        name = allocation.get_attribute(SLURM_ACCOUNT_ATTRIBUTE_NAME)
        if not name:
            name = "root"

        if name != self.name:
            raise SlurmError(
                f"Allocation {allocation} {SLURM_ACCOUNT_ATTRIBUTE_NAME} {name} does not match {self.name}"
            )

        child_accounts = set(allocation.get_attribute_list(SLURM_CHILDREN_ATTRIBUTE_NAME))
        if len(child_accounts) > 0 and allocation.allocationuser_set.count() > 0:
            raise SlurmError(
                f"Allocation {allocation} cannot be a parent and have users!"
                f" Please remove users or all {SLURM_CHILDREN_ATTRIBUTE_NAME} attributes."
            )

        self.specs += allocation.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)

        if len(child_accounts) > 0:
            self.child_type = SlurmAccount
            for account_name in child_accounts:
                account = self.children.get(account_name, SlurmAccount(account_name))
                try:
                    child_allocation = res_allocations.get(
                        pk=AllocationAttribute.objects.get(
                            allocation_attribute_type=SLURM_ACCOUNT_ATTRIBUTE_TYPE, value=account_name
                        ).allocation.pk
                    )
                    account.add_allocation(child_allocation, res_allocations, user_specs=user_specs)
                except ObjectDoesNotExist:
                    raise SlurmError(
                        f"No allocation with {SLURM_ACCOUNT_ATTRIBUTE_TYPE}={account_name} in correct resource"  # Don't have an easy way to get the resource here
                    )

                self.add_child(account)
        else:
            self.child_type = SlurmUser
            allocation_user_specs = allocation.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
            for u in allocation.allocationuser_set.filter(status__name="Active"):
                user = SlurmUser(u.user.username)
                user.specs += allocation_user_specs
                user.specs += user_specs
                self.add_child(user)

    def add_child(self, child):
        if not self.child_type:
            self.child_type = type(child)
        else:
            if type(child) is not self.child_type:
                raise SlurmError(
                    f"Cannot assign child of type {type(child)} to parent with child_type {self.child_type}"
                )
        if child.name not in self.children:
            self.children[child.name] = child

        ch = self.children[child.name]
        ch.specs += child.specs
        self.children[child.name] = ch

    def get_account(self, account_name):
        if self.child_type != SlurmAccount:
            return None
        if account_name in self.children.keys():
            return self.children[account_name]
        for account in self.children.values():
            result = account.get_account(account_name)
            if result:
                return result
        return None

    def write(self, out):
        if self.name != "root":
            self._write(out, f"Account - '{self.name}':{self.format_specs()}\n")

    def write_children(self, out):
        self._write(out, f"Parent - '{self.name}'\n")
        for child in self.children.values():
            child.write(out)
        if self.child_type == SlurmUser:
            return
        for child in self.children.values():
            child.write_children(out)


class SlurmUser(SlurmBase):
    @staticmethod
    def new_from_sacctmgr(line):
        """Create a new SlurmUser by parsing a line from sacctmgr dump. For
        example: User - 'jane':DefaultAccount='physics':Fairshare=Parent:QOS='general-compute'"""
        if not re.match("^User - '[^']+'", line):
            raise SlurmParserError(f'Invalid format. Must start with "User" for line: {line}')

        parts = line.split(":")
        name = re.sub(r"^User - ", "", parts[0]).strip("\n'")
        if len(name) == 0:
            raise SlurmParserError("User name not found for line: {line}")

        return SlurmUser(name, specs=parts[1:])

    def write(self, out):
        self._write(out, f"User - '{self.name}':{self.format_specs()}\n")
