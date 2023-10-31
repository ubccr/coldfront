""" Exports user information in a format that can be imported
    into  Open XDMoD """
import logging
import os
import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """ Output user information for all users """
    help = 'Export ColdFront data to XDMoD'

    def add_arguments(self, parser):
        parser.add_argument("-o", "--output", help="Path to output directory")

    def handle(self, *args, **options):
        verbosity = int(options['verbosity'])
        root_logger = logging.getLogger('')
        if verbosity == 0:
            root_logger.setLevel(logging.ERROR)
        elif verbosity == 2:
            root_logger.setLevel(logging.INFO)
        elif verbosity == 3:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.WARN)

        out_dir = None
        if options['output']:
            out_dir = options['output']
            if not os.path.isdir(out_dir):
                os.mkdir(out_dir, 0o0700)

            logger.warning("Writing output to directory: %s", out_dir)

        data = [['username', 'first_name', 'last_name', 'email', 'is_pi']]
        for user in User.objects.all():
            if user:
                data.append([
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.email,
                    user.userprofile.is_pi
                ])

        output = {
           'schema_version': 1,
           'datasource': 'coldfront ' + settings.VERSION,
           'data': data
        }

        if out_dir:
            with open(os.path.join(out_dir, 'names.json'), 'w') as filep:
                json.dump(output, filep, indent=4, separators=(",", ": "))
        else:
            print(json.dumps(output, indent=4, separators=(",", ": ")))
