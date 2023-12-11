# -*- coding: utf-8 -*-

'''
Daemon that watches for unseen ifxapps mailings
'''
import logging
from time import sleep
from django.db import connection
from django.conf import settings
from django.core.management.base import BaseCommand
from ifxbilling.fiine import handle_fiine_ifxapps_messages
from ifxuser.nanites import handleNanitesIfxappsMessages
from ifxmail.client import API as IfxMailAPI


logger = logging.getLogger(__name__)

DEFAULT_SLEEP_SECONDS = settings.PROCESS_IFXAPPS_MESSAGES_SLEEP_SECONDS if hasattr(settings, 'PROCESS_IFXAPPS_MESSAGES_SLEEP_SECONDS') else 5
MAX_SLEEP_SECONDS = 120

class Command(BaseCommand):
    '''
    Process messages from ifxapps@fas.harvard.edu on ifxmail
    '''
    help = 'Daemon that watches for ifxapps mail messages and runs processing for them Usage:\n' + \
        "./manage.py processIfxappsMessages"

    def add_arguments(self, parser):
        parser.add_argument(
            '--sleep-seconds',
            default=DEFAULT_SLEEP_SECONDS,
            help='Number of seconds to sleep between checks for messages',
        )

    def handle(self, *args, **kwargs):
        '''
        Daemon
        '''
        sleep_seconds = kwargs.get('sleep_seconds')

        while True:
            try:
                # Get unseen ifxmailings
                not_seen = IfxMailAPI.getUnseen()
                fiine_messages = []
                nanites_messages = []

                if not_seen:
                    logger.info(f'Found {len(not_seen)} messages to process')

                # Process unseen messages
                for message in not_seen:
                    message_data = message.to_dict()
                    subject = message_data['subject']
                    if subject:
                        if subject.startswith('fiine'):
                            fiine_messages.append(message_data)
                        elif subject.startswith('nanites'):
                            nanites_messages.append(message_data)

                if fiine_messages:
                    successes, errors = handle_fiine_ifxapps_messages(fiine_messages)
                    if successes:
                        logger.info(f'Successfully processed {successes} fiine updates')
                    if errors:
                        logger.error(f'Error processing fiine messages: \n{errors}')
                if nanites_messages:
                    successes, errors = handleNanitesIfxappsMessages(nanites_messages)
                    if successes:
                        logger.info(f'Successfully processed {successes} nanites updates')
                    if errors:
                        logger.error(f'Error processing nanites messages: \n{errors}')

                if sleep_seconds > kwargs.get('sleep_seconds'):
                    sleep_seconds = round(sleep_seconds / 2)
            except Exception as e:
                if 'Failed to establish' in str(e):
                    logger.error(f'Cannot connect to ifxmail: {e}')
                    if sleep_seconds < MAX_SLEEP_SECONDS:
                        sleep_seconds = sleep_seconds * 2
                logger.error(e)

            sleep(sleep_seconds)
            connection.close()
