import logging

from coldfront.plugins.update_user_profiles.utils import update_all_user_profiles

logger = logging.getLogger(__name__)


def run_update_user_profiles():
    logger.info('Updating user profiles...')
    update_all_user_profiles()
    logger.info('Update complete')
