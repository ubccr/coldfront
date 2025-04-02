import requests
import logging

from coldfront.core.utils.common import import_from_settings


logger = logging.getLogger(__name__)


SLACK_MESSAGING_ENABLED = import_from_settings('SLACK_MESSAGING_ENABLED', False)
if SLACK_MESSAGING_ENABLED:
    SLACK_WEBHOOK_URL = import_from_settings('SLACK_WEBHOOK_URL')


def send_message(text):
    if not SLACK_MESSAGING_ENABLED:
        return

    if not SLACK_WEBHOOK_URL:
        logger.error('Failed to send Slack notification. SLACK_WEBHOOK_URL is not set.')
        return

    data = {'text': text}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=data)
        response.raise_for_status()
    except requests.HTTPError as http_error:
        logger.error(f'HTTP error: failed to send Slack notification. {http_error}.')
    except Exception as err:
        logger.error(f'Error: failed to send Slack notification. {err}.')
