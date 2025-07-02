# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import logging
import shlex
import subprocess
from io import StringIO

from coldfront.core.utils.common import import_from_settings

SLURM_CLUSTER_ATTRIBUTE_NAME = import_from_settings("SLURM_CLUSTER_ATTRIBUTE_NAME", "slurm_cluster")
SLURM_ACCOUNT_ATTRIBUTE_NAME = import_from_settings("SLURM_ACCOUNT_ATTRIBUTE_NAME", "slurm_account_name")
SLURM_SPECS_ATTRIBUTE_NAME = import_from_settings("SLURM_SPECS_ATTRIBUTE_NAME", "slurm_specs")
SLURM_USER_SPECS_ATTRIBUTE_NAME = import_from_settings("SLURM_USER_SPECS_ATTRIBUTE_NAME", "slurm_user_specs")
SLURM_SACCTMGR_PATH = import_from_settings("SLURM_SACCTMGR_PATH", "/usr/bin/sacctmgr")
SLURM_CMD_REMOVE_USER = SLURM_SACCTMGR_PATH + " -Q -i delete user where name={} cluster={} account={}"
SLURM_CMD_REMOVE_QOS = SLURM_SACCTMGR_PATH + " -Q -i modify user where name={} cluster={} account={} set {}"
SLURM_CMD_REMOVE_ACCOUNT = SLURM_SACCTMGR_PATH + " -Q -i delete account where name={} cluster={}"
SLURM_CMD_ADD_ACCOUNT = SLURM_SACCTMGR_PATH + " -Q -i create account name={} cluster={}"
SLURM_CMD_ADD_USER = SLURM_SACCTMGR_PATH + " -Q -i create user name={} cluster={} account={}"
SLURM_CMD_CHECK_ASSOCIATION = (
    SLURM_SACCTMGR_PATH + " list associations User={} Cluster={} Account={} Format=Cluster,Account,User,QOS -P"
)
SLURM_CMD_LIST_ACCOUNTS = SLURM_SACCTMGR_PATH + " list associations User={} Cluster={} Format=Account -Pn"
SLURM_CMD_CHECK_DEFAULT_ACCOUNT = SLURM_SACCTMGR_PATH + " show user User={} Cluster={} Format=DefaultAccount -Pn"
SLURM_CMD_CHANGE_DEFAULT_ACCOUNT = (
    SLURM_SACCTMGR_PATH + " -Q -i modify user User={} where Cluster={} set DefaultAccount={}"
)
SLURM_CMD_BLOCK_ACCOUNT = SLURM_SACCTMGR_PATH + " -Q -i modify account {} where Cluster={} set GrpSubmitJobs=0"
SLURM_CMD_DUMP_CLUSTER = SLURM_SACCTMGR_PATH + " dump {} file={}"

logger = logging.getLogger(__name__)


class SlurmError(Exception):
    pass


def _run_slurm_cmd(cmd, noop=True):
    if noop:
        logger.warning("NOOP - Slurm cmd: %s", cmd)
        return

    try:
        result = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        if "Nothing deleted" in str(e.stdout):
            # We tried to delete something that didn't exist. Don't throw error
            logger.warning("Nothing to delete: %s", cmd)
            return e.stdout
        if "Nothing new added" in str(e.stdout):
            # We tried to add something that already exists. Don't throw error
            logger.warning("Nothing new to add: %s", cmd)
            return e.stdout

        logger.error("Slurm command failed: %s", cmd)
        err_msg = "return_value={} stdout={} stderr={}".format(e.returncode, e.stdout, e.stderr)
        raise SlurmError(err_msg)

    logger.debug("Slurm cmd: %s", cmd)
    logger.debug("Slurm cmd output: %s", result.stdout)

    return result.stdout


def slurm_remove_assoc(user, cluster, account, noop=False):
    # check default account
    cmd = SLURM_CMD_CHECK_DEFAULT_ACCOUNT.format(shlex.quote(user), shlex.quote(cluster))
    output = _run_slurm_cmd(cmd, noop=noop)
    default = ""
    with StringIO(output.decode("UTF-8")) as fh:
        default = fh.getvalue().strip()

    if default != account:
        _remove_assoc(user=user, cluster=cluster, account=account, noop=noop)
        return

    # get accounts
    cmd = SLURM_CMD_LIST_ACCOUNTS.format(shlex.quote(user), shlex.quote(cluster))
    output = _run_slurm_cmd(cmd, noop=noop)
    accounts = []
    with StringIO(output.decode("UTF-8")) as fh:
        reader = fh.getvalue()
        for line in reader.splitlines():
            accounts += [line]

    for userAccount in accounts:
        if userAccount != account:
            cmd = SLURM_CMD_CHANGE_DEFAULT_ACCOUNT.format(
                shlex.quote(user), shlex.quote(cluster), shlex.quote(userAccount)
            )
            _run_slurm_cmd(cmd, noop=noop)
            break

    _remove_assoc(user=user, cluster=cluster, account=account, noop=noop)


def _remove_assoc(user, cluster, account, noop=False):
    cmd = SLURM_CMD_REMOVE_USER.format(shlex.quote(user), shlex.quote(cluster), shlex.quote(account))
    _run_slurm_cmd(cmd, noop=noop)


def slurm_remove_qos(user, cluster, account, qos, noop=False):
    cmd = SLURM_CMD_REMOVE_QOS.format(shlex.quote(user), shlex.quote(cluster), shlex.quote(account), shlex.quote(qos))
    _run_slurm_cmd(cmd, noop=noop)


def slurm_remove_account(cluster, account, noop=False):
    cmd = SLURM_CMD_REMOVE_ACCOUNT.format(shlex.quote(account), shlex.quote(cluster))
    _run_slurm_cmd(cmd, noop=noop)


def slurm_add_assoc(user, cluster, account, specs=None, noop=False):
    if specs is None:
        specs = []
    cmd = SLURM_CMD_ADD_USER.format(shlex.quote(user), shlex.quote(cluster), shlex.quote(account))
    if len(specs) > 0:
        cmd += " " + " ".join(specs)
    _run_slurm_cmd(cmd, noop=noop)


def slurm_add_account(cluster, account, specs=None, noop=False):
    if specs is None:
        specs = []
    cmd = SLURM_CMD_ADD_ACCOUNT.format(shlex.quote(account), shlex.quote(cluster))
    if len(specs) > 0:
        cmd += " " + " ".join(specs)
    _run_slurm_cmd(cmd, noop=noop)


def slurm_block_account(cluster, account, noop=False):
    cmd = SLURM_CMD_BLOCK_ACCOUNT.format(shlex.quote(account), shlex.quote(cluster))
    _run_slurm_cmd(cmd, noop=noop)


def slurm_check_assoc(user, cluster, account):
    cmd = SLURM_CMD_CHECK_ASSOCIATION.format(shlex.quote(user), shlex.quote(cluster), shlex.quote(account))
    output = _run_slurm_cmd(cmd, noop=False)

    with StringIO(output.decode("UTF-8")) as fh:
        reader = csv.DictReader(fh, delimiter="|")
        for row in reader:
            if row["User"] == user and row["Account"] == account and row["Cluster"] == cluster:
                return True

    return False


def slurm_dump_cluster(cluster, fname, noop=False):
    cmd = SLURM_CMD_DUMP_CLUSTER.format(shlex.quote(cluster), shlex.quote(fname))
    _run_slurm_cmd(cmd, noop=noop)
