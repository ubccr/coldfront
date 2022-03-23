import logging
import shlex
import subprocess
import csv
from io import StringIO

from coldfront.core.utils.common import import_from_settings

SLURM_CLUSTER_ATTRIBUTE_NAME = import_from_settings('SLURM_CLUSTER_ATTRIBUTE_NAME', 'slurm_cluster')
SLURM_ACCOUNT_ATTRIBUTE_NAME = import_from_settings('SLURM_ACCOUNT_ATTRIBUTE_NAME', 'slurm_account_name')
SLURM_ACCOUNT_PARENT_ATTRIBUTE_NAME = import_from_settings(
    'SLURM_ACCOUNT_PARENT_ATTRIBUTE_NAME', 'slurm_parent_account_name')
SLURM_SPECS_ATTRIBUTE_NAME = import_from_settings('SLURM_SPECS_ATTRIBUTE_NAME', 'slurm_specs')
SLURM_USER_SPECS_ATTRIBUTE_NAME = import_from_settings('SLURM_USER_SPECS_ATTRIBUTE_NAME', 'slurm_user_specs')
SLURM_SACCTMGR_PATH = import_from_settings('SLURM_SACCTMGR_PATH', '/usr/bin/sacctmgr')

SLURM_CMD_ADD_CLUSTER = SLURM_SACCTMGR_PATH + ' -Q -i create cluster name={}'
SLURM_CMD_DUMP_CLUSTER = SLURM_SACCTMGR_PATH + ' dump {} file={}'
SLURM_CMD_MODIFY_CLUSTER = SLURM_SACCTMGR_PATH + ' -Q -i modify cluster where cluster={} set'
SLURM_CMD_REMOVE_CLUSTER = SLURM_SACCTMGR_PATH + ' -Q -i delete cluster where cluster={}'

SLURM_CMD_ADD_ACCOUNT = SLURM_SACCTMGR_PATH + ' -Q -i create account name={} cluster={}'
SLURM_CMD_BLOCK_ACCOUNT = SLURM_SACCTMGR_PATH + ' -Q -i modify account where cluster={} account={} set GrpSubmitJobs=0'
SLURM_CMD_MODIFY_ACCOUNT = SLURM_SACCTMGR_PATH + ' -Q -i modify account where cluster={} account={} set'
SLURM_CMD_REMOVE_ACCOUNT = SLURM_SACCTMGR_PATH + ' -Q -i delete account where name={} cluster={}'

SLURM_CMD_ADD_USER = SLURM_SACCTMGR_PATH + ' -Q -i create user name={} cluster={} account={}'
SLURM_CMD_MODIFY_USER = SLURM_SACCTMGR_PATH + ' -Q -i modify user where cluster={} account={} user={} set'
SLURM_CMD_REMOVE_USER = SLURM_SACCTMGR_PATH + ' -Q -i delete user where name={} cluster={} account={}'
SLURM_CMD_REMOVE_QOS = SLURM_SACCTMGR_PATH + ' -Q -i modify user where name={} cluster={} account={} set {}'
SLURM_CMD_CHECK_ASSOCIATION = SLURM_SACCTMGR_PATH + ' list associations User={} Cluster={} Account={} Format=Cluster,Account,User,QOS -P'

logger = logging.getLogger(__name__)

class SlurmError(Exception):
    pass

def _run_slurm_cmd(cmd, noop=True):
    """Run specified (sacctmgr) command.

    Honors the noop flag, in which case no command is executed,
    but logs and returns a text string containing the command which would
    have been run.

    Otherwise, on success, returns the std output of the 
    command (as a bytes sequence).  The cases wherein one
    tries to delete a non-existant Slurm entity or add an
    existing Slurm entity are not treated as errors (even
    though sacctmgr will yield a non-zero exit code).

    Other errors will cause a SlurmError to be raised. 
    """
    if noop:
        logger.warn('NOOP - Slurm cmd: %s', cmd)
        return "{}\n".format(cmd)

    try:
        result = subprocess.run(
            shlex.split(cmd), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=True)
    except subprocess.CalledProcessError as e:
        if 'Nothing deleted' in str(e.stdout):
            # We tried to delete something that didn't exist. Don't throw error
            logger.warn('Nothing to delete: %s', cmd)
            return e.stdout
        if 'Nothing new added' in str(e.stdout):
            # We tried to add something that already exists. Don't throw error
            logger.warn('Nothing new to add: %s', cmd)
            return e.stdout

        logger.error('Slurm command failed: %s', cmd)
        err_msg = 'return_value={} stdout={} stderr={}'.format(
            e.returncode, e.stdout, e.stderr)
        raise SlurmError(err_msg)

    logger.debug('Slurm cmd: %s', cmd)
    logger.debug('Slurm cmd output: %s', result.stdout)

    return result.stdout

# Cluster commands
def slurm_add_cluster(cluster, specs=None, noop=False):
    """Run the sacctmgr command to add the named cluster.

    The elements in specs will be added to the sacctmgr command
    to allow for setting options on the root association of the
    cluster.

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    if specs is None:
        specs = []
    cmd = SLURM_CMD_ADD_CLUSTER.format(shlex.quote(cluster))
    cmd += ' ' + ' '.join(map(lambda x: shlex.quote(x), specs))
    return _run_slurm_cmd(cmd, noop=noop)

def slurm_dump_cluster(cluster, fname, noop=False):
    """Run the sacctmgr command to dump the named cluster to named file.

    Runs the sacctmgr dump command for named cluster, saving dump
    to file fname.

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    cmd = SLURM_CMD_DUMP_CLUSTER.format(
        shlex.quote(cluster), 
        shlex.quote(fname))
    return _run_slurm_cmd(cmd, noop=noop)

def slurm_modify_cluster(cluster, specs=None, noop=False):
    """Run the sacctmgr command to modify the named cluster.

    This will run the sacctmgr command to modify the cluster
    named cluster, setting the values of fields in specs.
    Specs should be a list of 'foo=x' style strings.  Specs
    must be given and must be non-empty.

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    if specs is None or len(specs) == 0:
        raise SlurmError('slurm_modify_cluster requires non-empty specs list')
    cmd = SLURM_CMD_MODIFY_CLUSTER.format(shlex.quote(cluster))
    cmd += ' ' + ' '.join(map(lambda x: shlex.quote(x), specs))
    return _run_slurm_cmd(cmd, noop=noop)

def slurm_remove_cluster(cluster, noop=False):
    """Run the sacctmgr command to remove the named cluster.

    This will run the sacctmgr command to remove the cluster
    named cluster.

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    cmd = SLURM_CMD_REMOVE_CLUSTER.format(shlex.quote(cluster))
    return _run_slurm_cmd(cmd, noop=noop)

# Association commands
def slurm_add_assoc(user, cluster, account, specs=None, noop=False):
    """Run the sacctmgr command to add association for (user,cluster,account).

    This will run the sacctmgr add/create command to create an
    association for the triplet (user, cluster, account).  If specs is
    given, should be a list ref of strings of the form "foo=x", which
    will be added to the command.

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    if specs is None:
        specs = []
    import sys
    cmd = SLURM_CMD_ADD_USER.format(
            shlex.quote(user), 
            shlex.quote(cluster), 
            shlex.quote(account))
    if len(specs) > 0:
        cmd += ' ' + ' '.join(map(lambda x: shlex.quote(x), specs))
    return _run_slurm_cmd(cmd, noop=noop)

def slurm_check_assoc(user, cluster, account):
    """Checks if an association for (user,cluster,account) exists in Slurm.

    This will run a sacctmgr command to query for the existance of
    an association for the specified user, cluster, and account exists
    in the Slurm/sacctmgr database.  Returns true if it exists, false
    otherwise.

    This runs *always* --- no noop flag.  As it only queries Slurm
    and does not change anything, this should be fine.
    """
    cmd = SLURM_CMD_CHECK_ASSOCIATION.format(shlex.quote(user), shlex.quote(cluster), shlex.quote(account))
    output = _run_slurm_cmd(cmd, noop=False) 

    with StringIO(output.decode("UTF-8")) as fh:
        reader = csv.DictReader(fh, delimiter='|')
        for row in reader:
            if row['User'] == user and row['Account'] == account and row['Cluster'] == cluster:
                return True

    return False

def slurm_modify_assoc(user, cluster, account, specs=None, noop=False):
    """Run the sacctmgr command to modify the assoc (user, cluster, account)

    This will run the sacctmgr command to modify the association with
    the triplet (user, cluster, account), setting the values of fields
    in specs.  Specs should be a list of 'foo=x' style strings.  Specs
    must be given and must be non-empty.

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    if specs is None or len(specs) == 0:
        raise SlurmError('slurm_modify_assoc requires non-empty specs list')
    cmd = SLURM_CMD_MODIFY_USER.format(
        shlex.quote(cluster),
        shlex.quote(account),
        shlex.quote(user),)
    specs.sort()
    cmd += ' ' + ' '.join(map(lambda x: shlex.quote(x), specs))
    return _run_slurm_cmd(cmd, noop=noop)

def slurm_remove_assoc(user, cluster, account, noop=False):
    """Run the sacctmgr command to remove association for (user,cluster,account).

    This will run the sacctmgr command to remove an
    association for the triplet (user, cluster, account). 

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    cmd = SLURM_CMD_REMOVE_USER.format(
        shlex.quote(user), 
        shlex.quote(cluster), 
        shlex.quote(account))
    return _run_slurm_cmd(cmd, noop=noop)

# QoS commands
def slurm_remove_qos(user, cluster, account, qos, noop=False):
    """Run the sacctmgr command to remove the named QoS from specified user. ???

    ??? This command seems overly generic for the name ???

    This will run the sacctmgr command to remove an QoS from the
    association for the triplet (user, cluster, account).  The
    QoS argument should be of the form "QoS=qos1,qos2" where
    qos1, and qos2 are QoSes to keep, or the form "QoS-=qos3,qos4"
    where qos3 and qos4 are QoSes to remove.

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    cmd = SLURM_CMD_REMOVE_QOS.format(
        shlex.quote(user), 
        shlex.quote(cluster), 
        shlex.quote(account), 
        shlex.quote(qos))
    return _run_slurm_cmd(cmd, noop=noop)

# Account commands
def slurm_add_account(cluster, account, specs=None, parent=None, noop=False):
    """Run the sacctmgr command to add the named Slurm account in cluster.

    This will run the sacctmgr add/create command to create a Slurm
    account named account in cluster named cluster.  If specs is
    given, should be a list ref of strings of the form "foo=x", which
    will be added to the command.

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    if specs is None:
        specs = []
    cmd = SLURM_CMD_ADD_ACCOUNT.format(
        shlex.quote(account), 
        shlex.quote(cluster))
    if len(specs) > 0:
        cmd += ' ' + ' '.join(map(lambda x: shlex.quote(x), specs))
    if parent is not None:
        if parent.name != 'root':
            cmd += 'Parent={}'.format(shlex.quote(parent.name))
    return _run_slurm_cmd(cmd, noop=noop)

def slurm_modify_account(cluster, account, specs=None, noop=False):
    """Run the sacctmgr command to modify the named account in cluster.

    This will run the sacctmgr command to modify the named account 
    in cluster, setting the values of fields in specs.
    Specs should be a list of 'foo=x' style strings.  Specs
    must be given and must be non-empty.  Specs can and should include
    changes in the account parent ('parent=xxx' elements) if needed.

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    if specs is None or len(specs) == 0:
        raise SlurmError('slurm_modify_account requires non-empty specs list')
    cmd = SLURM_CMD_MODIFY_ACCOUNT.format(
        shlex.quote(cluster),
        shlex.quote(account))
    cmd += ' ' + ' '.join(map(lambda x: shlex.quote(x), specs))
    return _run_slurm_cmd(cmd, noop=noop)

def slurm_remove_account(cluster, account, noop=False):
    """Run the sacctmgr command to remove the named Slurm account in cluster.

    This will run the sacctmgr command to remove a Slurm account named account
    in cluster cluster.

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    cmd = SLURM_CMD_REMOVE_ACCOUNT.format(
        shlex.quote(account), 
        shlex.quote(cluster))
    return _run_slurm_cmd(cmd, noop=noop)

def slurm_block_account(cluster, account, noop=False):
    """Run the sacctmgr command to disable the named Slurm account in cluster.

    This will run the sacctmgr add/create command to disable a Slurm account
    (prevent jobs charging against the Slurm account from being submitted/run),
    without deleting the account.  Basically, it just sets GrpSubmitJobs to 0
    for the account.

    Basically a wrapper around _run_slurm_cmd(), see that method
    for more info.

    Honors the noop flag (in which case nothing done, but logs
    commands which would have been run).  Raises SlurmError on
    errors, otherwise returns stdout of the command being run.
    """
    cmd = SLURM_CMD_BLOCK_ACCOUNT.format(
        shlex.quote(account), 
        shlex.quote(cluster))
    return _run_slurm_cmd(cmd, noop=noop)

