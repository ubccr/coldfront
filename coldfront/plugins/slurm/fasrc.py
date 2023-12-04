"""FASRC-specific utils for the slurm library"""
import struct
import shlex
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.fasrc import get_quarter_start_end
from coldfront.plugins.slurm.utils import _run_slurm_cmd
from coldfront.plugins.slurm.associations import SlurmCluster

SLURM_SSHARE_PATH = import_from_settings('SLURM_SSHARE_PATH', '/usr/bin/sshare')
SLURM_SREPORT_PATH = import_from_settings('SLURM_SREPORT_PATH', '/usr/bin/sreport')
SLURM_CMD_PULL_FAIRSHARE = SLURM_SSHARE_PATH + ' -a -o "Cluster,Account%25,User%25,RawShares,NormShares,RawUsage,EffectvUsage,FairShare"'
SLURM_CMD_PULL_SREPORT = SLURM_SREPORT_PATH + '-T gres/gpu,cpu cluster accountutilization format="Cluster,Account%25,Login%25,TRESname,Used" start={}T00:00:00 end=now -t hours'

class SlurmClusterFasrc(SlurmCluster):
    """SlurmAccountFasrc adds sshare and sreport data to SlurmAccount model."""

    def pull_fairshares(self):
        """append sshare fairshare data to accounts and users"""
        fairshares = slurm_collect_fairshares(cluster=self.name)
        # select all fairshare lines with no user val, pin to SlurmAccounts.
        acct_fairshares = [d for d in fairshares if not d['User']]
        # pair acct_fairshares with SlurmAccounts
        for acct_share in acct_fairshares:
            account = next([a for a in self.accounts if a.name == acct_share['Account']], None)
            user_shares = [d for d in fairshares if d['Account'] == account.name and d['User']]
            for user_share in user_shares:
                user = next(u for u in account.users if u.name == user_share['User'])
                if not user:
                    print(f"no user for {user_share}")
                    continue
                if not hasattr(user, 'fairshare_dict'):
                    user.fairshare_dict = user_share
                else:
                    print("OVERWRITE BLOCKED:", user, user.fairshare_dict, user_share)
            if not account:
                print(f"no account for {acct_share}")
                continue
            if not hasattr(account, 'fairshare_dict'):
                account.fairshare_dict = acct_share
            else:
                print("OVERWRITE BLOCKED:", account, account.fairshare_dict, acct_share)

    def pull_usage(self):
        """append sreport usage data to accounts and users"""
        usages = slurm_collect_usage(cluster=self.name)
        acct_usages = [d for d in usages if not d['Login']]
        for acct_usage in acct_usages:
            account = next([a for a in self.accounts if a.name == acct_usage['Account']], None)
            user_usages = [d for d in usages if d['Account'] == account.name and d['Login']]
            for user_usage in user_usages:
                user = next(u for u in account.users if u.name == user_usage['Login'])
                if not user:
                    print(f"no user for {user_usage}")
                    continue
                if not hasattr(user, 'usage_dict'):
                    user.usage_dict = user_usage
                else:
                    print("OVERWRITE BLOCKED:", user, user.usage_dict, user_usage)
            if not account:
                print(f"no account for {acct_usage}")
                continue
            if not hasattr(account, 'usage_dict'):
                account.usage_dict = acct_usage
            else:
                print("OVERWRITE BLOCKED:", account, account.usage_dict, acct_usage)


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


def slurm_collect_fairshares(cluster=None, output_file=None):
    """collect fairshares for all accounts. Can specify a cluster if needed."""
    cluster_str = f' -M {cluster}' if cluster else ''
    output_str = f' > {output_file}' if output_file else ''
    cmd = SLURM_CMD_PULL_FAIRSHARE + cluster_str + output_str

    fairshare_data = _run_slurm_cmd(cmd)
    fairshare_data = fairshare_data.decode('utf-8').split('\n')
    fairshare_data = slurm_fixed_width_lines_to_dict(fairshare_data)
    return fairshare_data
