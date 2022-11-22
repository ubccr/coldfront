import logging

from coldfront.plugins.sftocf.utils import pull_sf, push_cf, pull_sf_push_cf_redash

logger = logging.getLogger(__name__)


def pull_sf_push_cf(volume=None, clean=False):
    filepaths = pull_sf(volume=volume)
    push_cf(filepaths, clean)
