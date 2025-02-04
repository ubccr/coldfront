import logging
import shlex
import struct
import subprocess
import csv
from io import StringIO

from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.fasrc import get_quarter_start_end

SLURM_CLUSTER_ATTRIBUTE_NAME = import_from_settings(
    'SLURM_CLUSTER_ATTRIBUTE_NAME', 'slurm_cluster')
SLURM_ACCOUNT_ATTRIBUTE_NAME = import_from_settings(
    'SLURM_ACCOUNT_ATTRIBUTE_NAME', 'slurm_account_name')
SLURM_SPECS_ATTRIBUTE_NAME = import_from_settings(
    'SLURM_SPECS_ATTRIBUTE_NAME', 'slurm_specs')
SLURM_USER_SPECS_ATTRIBUTE_NAME = import_from_settings(
    'SLURM_USER_SPECS_ATTRIBUTE_NAME', 'slurm_user_specs')
SLURM_SACCTMGR_PATH = import_from_settings(
    'SLURM_SACCTMGR_PATH', '/usr/bin/sacctmgr')
SLURM_SSHARE_PATH = import_from_settings('SLURM_SSHARE_PATH', '/usr/bin/sshare')
SLURM_SREPORT_PATH = import_from_settings('SLURM_SREPORT_PATH', '/usr/bin/sreport')
SLURM_SCONTROL_PATH = import_from_settings('SLURM_SCONTROL_PATH', '/usr/bin/scontrol')

SLURM_CMD_PULL_FAIRSHARE = SLURM_SSHARE_PATH + ' -a -o "Cluster,Account%30,User%25,RawShares,NormShares,RawUsage,EffectvUsage,FairShare"'
SLURM_CMD_PULL_SREPORT = SLURM_SREPORT_PATH + '-T gres/gpu,cpu cluster accountutilization format="Cluster,Account%25,Login%25,TRESname,Used" start={}T00:00:00 end=now -t hours'
SLURM_CMD_REMOVE_USER = SLURM_SACCTMGR_PATH + ' -Q -i delete user where name={} account={}'
SLURM_CMD_REMOVE_QOS = SLURM_SACCTMGR_PATH + ' -Q -i modify user where name={} cluster={} account={} set {}'
SLURM_CMD_EDIT_RAWSHARE= SLURM_SACCTMGR_PATH + ' -Q -i modify user set fairshare={} where name={} account={}'
SLURM_CMD_EDIT_ACCOUNT_RAWSHARE= SLURM_SACCTMGR_PATH + ' -Q -i modify account set fairshare={} where name={}'
SLURM_CMD_REMOVE_ACCOUNT = SLURM_SACCTMGR_PATH + ' -Q -i delete account where name={} cluster={}'
SLURM_CMD_ADD_ACCOUNT = SLURM_SACCTMGR_PATH + ' -Q -i create account name={} cluster={}'
SLURM_CMD_ADD_USER = SLURM_SACCTMGR_PATH + ' -Q -i create user name={} cluster={} account={}'
SLURM_CMD_CHECK_ASSOCIATION = SLURM_SACCTMGR_PATH + ' list associations User={} Cluster={} Account={} Format=Cluster,Account,User,QOS -P'
SLURM_CMD_BLOCK_ACCOUNT = SLURM_SACCTMGR_PATH + ' -Q -i modify account {} where Cluster={} set GrpSubmitJobs=0'
SLURM_CMD_DUMP_CLUSTER = SLURM_SACCTMGR_PATH + ' dump {} file={}'
SLURM_CMD_LIST_PARTITIONS = SLURM_SCONTROL_PATH + ' show partitions'


logger = logging.getLogger(__name__)


class SlurmError(Exception):
    pass

def slurm_list_partitions(noop=False):
    def get_process_partition_item_value(partition_item):
        item_values = partition_item.split('=')
        if len(item_values) == 2: # Item follows format: Nodes=cpn01
            return item_values[1]
        # Item follows format: TRESBillingWeights=CPU=1.0,Mem=0.25G
        item_name = f'{item_values[0]}='
        partition_item_values = partition_item.replace(item_name, '')
        return partition_item_values

    logger.debug(f'  Pulling Partition data')
    cmd = SLURM_CMD_LIST_PARTITIONS
    partitions = _run_slurm_cmd(cmd, noop=noop)

    partitions = partitions.decode('utf-8').split('\n\n')
    partitions = [element.replace('\n ', '').replace('  ', ' ') for element in partitions]
    partitions = [element.split(' ') for element in partitions]
    partitions = [element for element in partitions if element != ['']]
    partitions = [{item.split('=')[0]: get_process_partition_item_value(item) for item in fields} for fields in partitions]

    return partitions

def _run_slurm_cmd(cmd, noop=True, show_output=False):
    if noop:
        logger.warning('NOOP - Slurm cmd: %s', cmd)
        return

    try:
        result = subprocess.run(
            shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
    except subprocess.CalledProcessError as e:
        if 'Nothing deleted' in str(e.stdout):
            # We tried to delete something that didn't exist. Don't throw error
            logger.warning(f'Nothing to delete: {cmd}')
            return e.stdout
        if 'Nothing new added' in str(e.stdout):
            # We tried to add something that already exists. Don't throw error
            logger.warning(f'Nothing new to add: {cmd}')
            return e.stdout

        logger.error(f'Slurm command {cmd} failed: {cmd}')
        err_msg = 'return_value={} stdout={} stderr={}'.format(e.returncode, e.stdout, e.stderr)
        raise SlurmError(err_msg)
    logger.debug(f' \x1b[33;20m Slurm cmd: \x1b[31;1m {cmd} \x1b[0m')
    if show_output:
        logger.debug(f' \x1b[33;20m Slurm cmd output: \x1b[31;1m {result.stdout} \x1b[0m')

    return result.stdout

def slurm_remove_assoc(user, account, noop=False):
    cmd = SLURM_CMD_REMOVE_USER.format(
        shlex.quote(user), shlex.quote(account)
    )
    _run_slurm_cmd(cmd, noop=noop)

def slurm_remove_qos(user, cluster, account, qos, noop=False):
    cmd = SLURM_CMD_REMOVE_QOS.format(
        shlex.quote(user), shlex.quote(cluster), shlex.quote(account), shlex.quote(qos)
    )
    _run_slurm_cmd(cmd, noop=noop)

def slurm_update_raw_share(user,  account, raw_share, noop=False):
    cmd = SLURM_CMD_EDIT_RAWSHARE.format(
        shlex.quote(raw_share),
        user,
        account
    )
    return _run_slurm_cmd(cmd, noop=noop)

def slurm_update_account_raw_share(account, raw_share, noop=False):
    cmd = SLURM_CMD_EDIT_ACCOUNT_RAWSHARE.format(
        shlex.quote(raw_share),
        account
    )
    return _run_slurm_cmd(cmd, noop=noop)

def slurm_remove_account(cluster, account, noop=False):
    cmd = SLURM_CMD_REMOVE_ACCOUNT.format(shlex.quote(account), shlex.quote(cluster))
    _run_slurm_cmd(cmd, noop=noop)

def slurm_add_assoc(user, cluster, account, specs=None, noop=False):
    if specs is None:
        specs = []
    cmd = SLURM_CMD_ADD_USER.format(shlex.quote(user), shlex.quote(cluster), shlex.quote(account))
    if len(specs) > 0:
        cmd += ' ' + ' '.join(specs)
    _run_slurm_cmd(cmd, noop=noop)

def slurm_add_account(cluster, account, specs=None, noop=False):
    if specs is None:
        specs = []
    cmd = SLURM_CMD_ADD_ACCOUNT.format(shlex.quote(account), shlex.quote(cluster))
    if len(specs) > 0:
        cmd += ' ' + ' '.join(specs)
    _run_slurm_cmd(cmd, noop=noop)

def slurm_block_account(cluster, account, noop=False):
    cmd = SLURM_CMD_BLOCK_ACCOUNT.format(shlex.quote(account), shlex.quote(cluster))
    _run_slurm_cmd(cmd, noop=noop)

def slurm_check_assoc(user, cluster, account):
    cmd = SLURM_CMD_CHECK_ASSOCIATION.format(
        shlex.quote(user), shlex.quote(cluster), shlex.quote(account)
    )
    output = _run_slurm_cmd(cmd, noop=False)

    with StringIO(output.decode("UTF-8")) as fh:
        reader = csv.DictReader(fh, delimiter='|')
        for row in reader:
            if row['User'] == user and row['Account'] == account and row['Cluster'] == cluster:
                return True

    return False

def slurm_dump_cluster(cluster, fname, noop=False):
    cmd = SLURM_CMD_DUMP_CLUSTER.format(shlex.quote(cluster), shlex.quote(fname))
    _run_slurm_cmd(cmd, noop=noop)

def convert_to_dict(input_list):
    keys = input_list[0]
    data = input_list[2:]
    result = []
    for item in data:
        result.append(dict(zip(keys, item)))
    return result

def slurm_fixed_width_lines_to_dict(line_iterable):
    """Take a list of fixed-width lines and convert them to dictionaries.
    line_iterable's first item should be the header; second item, dashed width indicators.
    """
    widths = [n.count('-') + 1 for n in line_iterable[1].split()]
    fmtstring = ' '.join(f'{abs(fw)}s' for fw in widths)
    unpack = struct.Struct(fmtstring).unpack_from
    parse = lambda line: tuple(s.decode().strip() for s in unpack(line.encode()))
    # split each line by width
    line_iterable = [parse(line) for line in line_iterable if line]
    # pair values with headers
    return convert_to_dict(line_iterable)

def slurm_collect_usage(cluster=None, output_file=None):
    """collect usage for all accounts. Can specify a cluster if needed."""
    cluster_str = f' cluster {cluster}' if cluster else ''
    output_str = f' > {output_file}' if output_file else ''
    quarter_start, _ = get_quarter_start_end()
    cmd = SLURM_CMD_PULL_SREPORT.format(shlex.quote(quarter_start)) + cluster_str + output_str
    usage_data = _run_slurm_cmd(cmd)
    usage_data = usage_data.decode('utf-8').split('\n')
    header_idx = usage_data.index(next(l for l in usage_data if "TRES Name" in l))
    usage_data = usage_data[header_idx:]
    usage_data = slurm_fixed_width_lines_to_dict(usage_data)
    return usage_data

def slurm_collect_shares(cluster=None, output_file=None):
    """collect fairshares for all accounts. Can specify a cluster if needed."""
    cluster_str = f' -M {cluster}' if cluster else ''
    output_str = f' > {output_file}' if output_file else ''
    cmd = SLURM_CMD_PULL_FAIRSHARE + cluster_str + output_str

    logger.debug(f'  Pulling Share data for cluster {cluster}')
    share_data = _run_slurm_cmd(cmd, noop=False)
    share_data = share_data.decode('utf-8').split('\n')
    if "-----" not in share_data[1]:
        share_data = share_data[1:]
    share_data = slurm_fixed_width_lines_to_dict(share_data)
    return share_data
