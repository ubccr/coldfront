from coldfront.plugins.fasrc.utils import AllTheThingsConn

def import_quotas(volume=None, clean=False):
    attconn = AllTheThingsConn()
    result_file = attconn.pull_quota_data()
    attconn.push_quota_data(result_file)

