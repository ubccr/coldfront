from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV


INSTALLED_APPS += [ 'coldfront.plugins.fasrc' ]

NEO4JP = ENV.str('neo4jp')
