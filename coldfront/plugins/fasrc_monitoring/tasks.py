from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.fasrc_monitoring.utils import run_view_db_checks

def run_view_checks():
    username = import_from_settings('TEST_USER')
    password = import_from_settings('TEST_PASS')
    run_view_db_checks(username, password)
