<<<<<<< HEAD
import os
import sys

__version__ = '1.1.3'
VERSION = __version__


def manage():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coldfront.config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
=======
import os
import sys

__version__ = '1.1.4'
VERSION = __version__


def manage():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coldfront.config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
>>>>>>> upstream/main
