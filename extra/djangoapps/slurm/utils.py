import logging
import shlex
import subprocess
import csv
from io import StringIO

from common.djangolibs.utils import import_from_settings

SLURM_CLUSTER_ATTRIBUTE_NAME = import_from_settings('SLURM_CLUSTER_ATTRIBUTE_NAME', 'slurm_cluster')
SLURM_ACCOUNT_ATTRIBUTE_NAME = import_from_settings('SLURM_ACCOUNT_ATTRIBUTE_NAME', 'slurm_account_name')
SLURM_SPECS_ATTRIBUTE_NAME = import_from_settings('SLURM_SPECS_ATTRIBUTE_NAME', 'slurm_specs')
SLURM_USER_SPECS_ATTRIBUTE_NAME = import_from_settings('SLURM_USER_SPECS_ATTRIBUTE_NAME', 'slurm_user_specs')
SLURM_NOOP = import_from_settings('SLURM_NOOP', False)
SLURM_SACCTMGR_PATH = import_from_settings('SLURM_SACCTMGR_PATH', '/usr/bin/sacctmgr')
SLURM_CMD_REMOVE_USER = SLURM_SACCTMGR_PATH + ' -Q -i delete user where name={} cluster={} account={}'
SLURM_CMD_ADD_USER = SLURM_SACCTMGR_PATH + ' -Q -i create user name={} cluster={} account={}'
SLURM_CMD_CHECK_ASSOCIATION = SLURM_SACCTMGR_PATH + ' list associations User={} Cluster={} Account={} Format=Cluster,Account,User,QOS -P'
SLURM_CMD_BLOCK_ACCOUNT = SLURM_SACCTMGR_PATH + ' -Q -i modify account {} where Cluster={} set GrpSubmitJobs=0'

logger = logging.getLogger(__name__)

def _run_slurm_cmd(cmd, noop=True):
    if noop:
        logger.warn('NOOP - Slurm cmd: %s', cmd)
        return

    try:
        result = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as e:
        logger.error('Slurm command failed: %s', cmd)
        err_msg = 'return_value={} stdout={} stderr={}'.format(e.returncode, e.stdout, e.stderr)
        raise Exception(err_msg)

    logger.debug('Slurm cmd: %s', cmd)
    logger.debug('Slurm cmd output: %s', result.stdout)

    return result.stdout

def slurm_remove_assoc(user, cluster, account):
    cmd = SLURM_CMD_REMOVE_USER.format(user, cluster, account)
    _run_slurm_cmd(cmd, noop=SLURM_NOOP)

def slurm_add_assoc(user, cluster, account, specs=None):
    if specs is None:
        specs = []
    cmd = SLURM_CMD_ADD_USER.format(user, cluster, account)
    if len(specs) > 0:
        cmd += ' ' + ' '.join(specs)
    _run_slurm_cmd(cmd, noop=SLURM_NOOP)

def slurm_block_account(cluster, account):
    cmd = SLURM_CMD_BLOCK_ACCOUNT.format(account, cluster)
    _run_slurm_cmd(cmd, noop=SLURM_NOOP)

def slurm_check_assoc(user, cluster, account):
    cmd = SLURM_CMD_CHECK_ASSOCIATION.format(user, cluster, account)
    output = _run_slurm_cmd(cmd, noop=False) 

    with StringIO(output.decode("UTF-8")) as fh:
        reader = csv.DictReader(fh, delimiter='|')
        for row in reader:
            if row['User'] == user and row['Account'] == account and row['Cluster'] == cluster:
                return True

    return False
