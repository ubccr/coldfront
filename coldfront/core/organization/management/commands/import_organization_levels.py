import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from coldfront.core.organization.models import OrganizationLevel


class Command(BaseCommand):
    help = 'Import OrganizationLevels from a file'

    def add_arguments(self, parser):
        base_dir = settings.BASE_DIR
        def_input = os.path.join(base_dir, 'local_data',
                'organization_levels.csv')
        def_delimiter = '|'

        parser.add_argument('-i', '--input',
                help='Path to file containing OrganizationLevels to import. '
                    'Should one record per line, with fields '
                    'name,level,parent_name.  Defaults to {}'.format(def_input),
                default=def_input)
        parser.add_argument('--delimiter',
                help='Delimiter between fields in input file.  '
                    'Default is {}'.format(def_delimiter),
                default=def_delimiter)
        parser.add_argument('-d', '--delete',
                action='store_true',
                help='If provided, the command will first delete any existing '
                    'OrganizationLevels (and therefore Organizations) before '
                    'importing from file.  Default behave is not to delete, '
                    'so new entries will be appended to existing list of '
                    'OrganizationLevels.')
        return


    def handle(self, *args, **options):

        input_file = options['input']
        delim = options['delimiter']
        delete = options['delete']
        verbose = options['verbosity']

        linenum = 0
        sys.stderr.write('[TPTEST] Starting import_organization_level...\n')

        with open(input_file, 'r') as fp:
            if delete:
                OrganizationLevel.objects.all().delete()
            line = fp.readline()
            linenum += 1
            sys.stderr.write('[TPTEST] Read line #{}, "{}"...\n'.format(
                linenum, line))
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
                name = fields[0].strip()
                level = fields[1].strip()
                pname = fields[2].strip()
                if not pname:
                    pname = None

                try:
                    level = int(level)
                except ValueError:
                    raise CommandError('Illegal value for field "level", '
                            'got "{}", expecting integer, line {} of '
                            'file {}'.format(level, linenum, input_file))

                if pname is None:
                    tmp, created = OrganizationLevel.objects.get_or_create(
                            name=name, level=level, parent=None)
                else:
                    try:
                        parent = OrganizationLevel.objects.get(name=pname)
                    except ObjectDoesNotExist:
                        raise CommandError('Illegal value for field '
                                'parent_name, got "{}" but no '
                                'OrganizationLevel found with that name, '
                                'line {} of file {}'.format(pname, linenum,
                                    input_file))

                    tmp, created = OrganizationLevel.objects.get_or_create(
                        name=name,
                        level=level,
                        parent=parent)
                if verbose:
                    tmp_pname = '<no parent>'
                    if pname:
                        tmp_pname = pname
                    if created:
                        sys.stderr.write('[VERBOSE] Added OrganizationLevel '
                                'name={}, level={}, parent={}\n'.format(
                                    name, level, tmp_pname))
                    else:
                        sys.stderr.write('[VERBOSE] Skipping OrganizationLevel '
                                'name={}, level={}, parent={}; already '
                                'present\n'.format(name, level, tmp_pname))

                line = fp.readline()
                linenum += 1
        return
