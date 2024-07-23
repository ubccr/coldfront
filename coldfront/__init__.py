from __future__ import absolute_import, unicode_literals
import os
import sys


__version__ = '1.1.6'
VERSION = __version__
__all__ = ('celery_app',)
from .celery import app as celery_app


def manage():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coldfront.config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
