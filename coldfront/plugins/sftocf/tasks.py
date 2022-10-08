import logging
import os

from coldfront.plugins.sftocf.utils import ColdFrontDB

logger = logging.getLogger(__name__)


def pull_sf_push_cf(volume=None, clean=False):
    cfdb = ColdFrontDB()
    filepaths = cfdb.pull_sf(volume=volume)
    cfdb.push_cf(filepaths, clean)
