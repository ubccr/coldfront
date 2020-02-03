import functools
import os
import unittest


def _skipUnlessEnvDefined(varname, reason=None):
    skip = varname not in os.environ

    if skip and reason is None:
        reason = 'Automatically skipped. {} is not defined'.format(varname)

    return functools.partial(unittest.skipIf, skip, reason)


makes_remote_requests = _skipUnlessEnvDefined('TESTS_ALLOW_REMOTE_REQUESTS')
