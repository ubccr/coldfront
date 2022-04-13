import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from coldfront.core.organization.models import Organization
from coldfront.core.organization.models import Directory2Organization


class Command(BaseCommand):
    help = 'Import Directory2Organization strings from a file'

    def add_arguments(self, parser):
        base_dir = settings.BASE_DIR
        def_input = os.path.join(base_dir, 'local_data',
                'directory2organization.csv')
        def_delimiter = '|'

        parser.add_argument('-i', '--input',
                help='Path to file containing Directory2Organization string to '
                    'import. Should one record per line, with fields '
                    'fullcode for organization, and string associated with '
                    'it.'.format(def_input),
                default=def_input)
        parser.add_argument('--delimiter',
                help='Delimiter between fields in input file.  '
                    'Default is {}'.format(def_delimiter),
                default=def_delimiter)
        parser.add_argument('-d', '--delete',
                action='store_true',
                help='If provided, the command will first delete any existing '
                    'Directory2Organizations before '
                    'importing from file.  Default behave is not to delete, '
                    'so new entries will be appended to existing list of '
                    'Directory2Organizations.')
        return


    def handle(self, *args, **options):

        input_file = options['input']
        delim = options['delimiter']
        delete = options['delete']
        verbose = options['verbosity']

        linenum = 0

        with open(input_file, 'r') as fp:
            if delete:
                if verbose:
                    sys.stderr.write('[VERBOSE] Deleting old '
                        'Directory2Organizations\n')
                Directory2Organization.objects.all().delete()
            line = fp.readline()
            linenum += 1
            while line != '':
                line = line.strip()
                if not line:
                    line = fp.readline()
                    linenum += 1
                    continue
                if line.startswith('#'):
                    line = fp.readline()
                    linenum += 1
                    continue
                fields = line.split(delim)
                fullcode = fields[0].strip()
                dstring = fields[1].strip()

                org = Organization.get_organization_by_fullcode(fullcode)
                if org is None:
                    raise CommandError('Illegel value "{}" for fullcode, '
                            'line #{} of {}; no matching Organization '
                            'found'.format(fullcode, linenum, input_file))
                tmp, created = Directory2Organization.objects.get_or_create(
                        organization=org,
                        directory_string=dstring)

                if verbose:
                    if created:
                        sys.stderr.write('[VERBOSE] Added '
                            'Directory2Organization for {} => {}\n'.format(
                                dstring, fullcode))
                    else:
                        sys.stderr.write('[VERBOSE] Skipping '
                                'Directory2Organization for {} => {}\n'.format(
                                    dstring, fullcode))
                line = fp.readline()
                linenum += 1
        return
