from coldfront.plugins.fasrc.utils import AllTheThingsConn

def import_quotas(volumes=None):
    '''
    Collect group-level quota and usage data from ATT and insert it into the
    Coldfront database.

    Parameters
    ----------
    volumes : string of volume names separated by commas. Optional, default None
    '''
    if volumes:
        volumes = volumes.split(",")
    attconn = AllTheThingsConn()
    result_file = attconn.pull_quota_data(volumes=volumes)
    attconn.push_quota_data(result_file)
