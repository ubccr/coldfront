from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV


INSTALLED_APPS += [ 'coldfront.plugins.fasrc_monitoring' ]

TEST_USER = ENV.str('TEST_USER', '')
TEST_PASS = ENV.str('TEST_PASS', '')
