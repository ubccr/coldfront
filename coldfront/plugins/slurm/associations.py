# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import datetime
import logging
import os
import re
import sys
from typing import Optional, Self

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import QuerySet

from coldfront.core.allocation.models import Allocation, AllocationAttribute, AllocationAttributeType
from coldfront.core.resource.models import Resource
from coldfront.plugins.slurm.utils import (
    SLURM_ACCOUNT_ATTRIBUTE_NAME,
    SLURM_CHILDREN_ATTRIBUTE_NAME,
    SLURM_CLUSTER_ATTRIBUTE_NAME,
    SLURM_SPECS_ATTRIBUTE_NAME,
    SLURM_USER_SPECS_ATTRIBUTE_NAME,
    SlurmError,
    parse_qos,
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
        self.accounts: dict[str, SlurmAccount] = {}

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
                    parent_account.add_account(account)
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
                parent_account.add_user(user)

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
        # remove child accounts from cluster accounts
        child_accounts = set()
        for account in cluster.accounts.values():
            child_accounts.update(account.accounts.keys())
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
                child_accounts.update(account.accounts.keys())
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

    def get_objects_to_remove(self, expected: Self) -> dict[str, list[dict]]:
        """Get the objects to remove from this cluster based on the expected cluster"""
        objects_to_remove = {
            "users": [],
            "accounts": [],
            "qoses": [],
        }
        for account_name, account in self.accounts.items():
            if account_name == "root":
                continue
            child_objects_to_remove = account.get_objects_to_remove(expected.accounts.get(account_name))
            for key, value in child_objects_to_remove.items():
                objects_to_remove[key].extend(value)
        return objects_to_remove


class SlurmAccount(SlurmBase):
    def __init__(self, name, specs=None):
        super().__init__(name, specs=specs)
        self.users: dict[str, SlurmUser] = {}
        self.accounts: dict[str, SlurmAccount] = {}

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

    def add_allocation(self, allocation: Allocation, res_allocations: QuerySet[Allocation], user_specs=None):
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
        self.specs += allocation.get_attribute_list(SLURM_SPECS_ATTRIBUTE_NAME)

        for account_name in child_accounts:
            account = self.accounts.get(account_name, SlurmAccount(account_name))
            try:
                child_allocation = res_allocations.get(
                    pk=AllocationAttribute.objects.get(
                        allocation_attribute_type=AllocationAttributeType.objects.get(
                            name=SLURM_ACCOUNT_ATTRIBUTE_NAME
                        ),
                        value=account_name,
                    ).allocation.pk
                )
                account.add_allocation(child_allocation, res_allocations, user_specs=user_specs)
            except ObjectDoesNotExist:
                raise SlurmError(
                    f"No allocation with {SLURM_ACCOUNT_ATTRIBUTE_NAME}={account_name} in correct resource"  # Don't have an easy way to get the resource here
                )

            self.add_account(account)

        allocation_user_specs = allocation.get_attribute_list(SLURM_USER_SPECS_ATTRIBUTE_NAME)
        for u in allocation.allocationuser_set.filter(status__name="Active"):
            user = SlurmUser(u.user.username)
            user.specs += allocation_user_specs
            user.specs += user_specs
            self.add_user(user)

    def add_account(self, account: SlurmAccount) -> None:
        if account.name not in self.accounts:
            self.accounts[account.name] = account
            return
        self.accounts[account.name].specs += account.specs

    def add_user(self, user: SlurmUser) -> None:
        if user.name not in self.users:
            self.users[user.name] = user
            return
        self.users[user.name].specs += user.specs

    def get_account(self, account_name: str) -> Optional[SlurmAccount]:
        """Gets an account, traversing through child accounts"""
        if account_name in self.accounts.keys():
            return self.accounts[account_name]
        for account in self.accounts.values():
            result = account.get_account(account_name)
            if result:
                return result
        return None

    def write(self, out):
        if self.name != "root":
            self._write(out, f"Account - '{self.name}':{self.format_specs()}\n")

    def write_children(self, out):
        self._write(out, f"Parent - '{self.name}'\n")
        for user in self.users.values():
            user.write(out)
        for account in self.accounts.values():
            account.write(out)
        for account in self.accounts.values():
            account.write_children(out)

    def get_objects_to_remove(self, expected: Optional[Self] = None) -> dict[str, list[dict]]:
        """Get the objects to remove from this account based on the expected account.
        If expected is None, remove the entire account.
        """
        objects_to_remove = {
            "users": [],
            "accounts": [],
            "qoses": [],
        }

        if expected is None:
            for account in self.accounts.values():
                child_objects_to_remove = account.get_objects_to_remove()
                for key, value in child_objects_to_remove.items():
                    objects_to_remove[key].extend(value)
            for uid in self.users.keys():
                objects_to_remove["users"].append({"user": uid, "account": self.name})
            objects_to_remove["accounts"].append({"account": self.name})
            return objects_to_remove

        accounts_removed = 0
        for account_name, account in self.accounts.items():
            if account_name not in expected.accounts:
                accounts_removed += 1
            child_objects_to_remove = self.get_objects_to_remove(expected.accounts.get(account_name))
            for key, value in child_objects_to_remove.items():
                objects_to_remove[key].extend(value)

        users_removed = 0
        for uid, user in self.users.items():
            if uid == "root":
                continue
            if uid not in expected.users:
                objects_to_remove["users"].append({"user": uid, "account": self.name})
                users_removed += 1
            else:
                qoses_to_remove = user.get_qoses_to_remove(self.name, self.name, expected.users[uid])
                if len(qoses_to_remove) > 0:
                    objects_to_remove["qoses"].append(
                        {"user": uid, "account": self.name, "qos": "QOS-=" + ",".join(list(qoses_to_remove))}
                    )

        if accounts_removed == len(self.accounts) and users_removed == len(self.users):
            objects_to_remove["accounts"].append({"account": self.name})
        return objects_to_remove


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

    def get_qoses_to_remove(self, account_name: str, cluster_name: str, expected: Self) -> set[str]:
        """Get the set of QOSes to remove from this user based on the expected user
        Returns: set of QOS names to remove
        """
        logger.debug(
            f"diff qos: cluster={cluster_name}"
            f" account={account_name}"
            f" uid={self.name}"
            f" self={self.spec_list()}"
            f" expected={expected.spec_list()}"
        )

        specs_a = []
        for s in self.spec_list():
            if s.startswith("QOS"):
                specs_a += parse_qos(s)

        specs_b = []
        for s in expected.spec_list():
            if s.startswith("QOS"):
                specs_b += parse_qos(s)

        specs_set_a = set(specs_a)
        specs_set_b = set(specs_b)

        diff = specs_set_a.difference(specs_set_b)
        logger.debug(
            f"diff qos: cluster={cluster_name}"
            f" account={account_name}"
            f" uid={self.name}"
            f" self={self.spec_list()}"
            f" expected={expected.spec_list()}"
            f" diff={diff}"
        )

        return diff
