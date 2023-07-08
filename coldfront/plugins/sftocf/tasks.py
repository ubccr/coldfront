from coldfront.plugins.sftocf import utils

def pullsf_pushcf_redash():
    utils.pull_sf_push_cf_redash()

def pull_sf_push_cf(volume=None, clean=False):
    filepaths = utils.pull_sf(volume=volume)
    utils.push_cf(filepaths)

def pull_resource_data():
    utils.pull_resource_data()
