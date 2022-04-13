import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from coldfront.core.organization.models import OrganizationLevel
from coldfront.core.organization.models import Organization


class Command(BaseCommand):
    help = 'Import Organizations from a file'

    def add_arguments(self, parser):
        base_dir = settings.BASE_DIR
        def_input = os.path.join(base_dir, 'local_data',
                'organizations.csv')
        def_delimiter = '|'

        parser.add_argument('-i', '--input',
                help='Path to file containing Organization to import. '
                    'Should one record per line, with fields '
                    'code, orglevel, parent_code, shortname, longname, '
                    'selectable_user, selectable_project. '
                    'Defaults to {}'.format(def_input),
                default=def_input)
        parser.add_argument('--delimiter',
                help='Delimiter between fields in input file.  '
                    'Default is {}'.format(def_delimiter),
                default=def_delimiter)
        parser.add_argument('-d', '--delete',
                action='store_true',
                help='If provided, the command will first delete any existing '
                    'Organizations (and therefore Organizations) before '
                    'importing from file.  Default behave is not to delete, '
                    'so new entries will be appended to existing list of '
                    'Organizations.')
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
                    sys.stderr.write('[VERBOSE] Deleting old organizations\n')
                Organization.objects.all().delete()
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
                code = fields[0].strip()
                olname = fields[1].strip()
                pcode = fields[2].strip()
                short = fields[3].strip()
                long = fields[4].strip()
                select_user = fields[5].strip()
                select_proj = fields[6].strip()
                if not pcode:
                    pcode = None

                try:
                    orglevel = OrganizationLevel.objects.get(name=olname)
                except ObjectDoesNotExist:
                    raise CommandError('Illegal value for field '
                        'orglevel_name="{}"; no such OrganizationLevel '
                        'found; line={} of file={}\n'.format(
                            olname, linenum, input_file))

                parent_orglevel = orglevel.parent
                if parent_orglevel is None:
                    if pcode is not None:
                        raise CommandError('Illegal record; Organization of '
                                'level {} cannot have parent, but parent name '
                                '{} given, line={} of file={}\n'.format(
                                    orglevel.name, pcode, linenum, input_file))


                if pcode is None and parent_orglevel is None:
                    tmp, created = Organization.objects.get_or_create(
                        code=code,
                        shortname=short,
                        longname=long,
                        organization_level=orglevel,
                        is_selectable_for_user=select_user,
                        is_selectable_for_project=select_proj,)
                elif pcode is not None and parent_orglevel is not None:
                    tmp_porglevel_name = 'None'
                    if parent_orglevel:
                        tmp_prglevel_name = parent_orglevel.name
                    try:
                        parent=Organization.objects.get(
                            code=pcode,
                            organization_level=parent_orglevel)
                    except ObjectDoesNotExist:
                            raise CommandError('Illegal value parent="{}" but '
                                    'no such Organization at level={} found; '
                                    'line={} or file={}\n'.format(
                                        pcode, tmp_porglevel_name, linenum, 
                                        input_file))

                    tmp, created = Organization.objects.get_or_create(
                        code=code,
                        shortname=short,
                        longname=long,
                        organization_level=orglevel,
                        parent=parent,
                        is_selectable_for_user=select_user,
                        is_selectable_for_project=select_proj,)
                else:
                    # Something went wrong
                    if pcode:
                        raise CommandError('Error creating org code={} level={}; '
                                'line={} of file={}; parent_code={} given but '
                                'OrganizationLevel does not allow having a '
                                'parent'.format(code, orglevel.name,
                                    linenum, input_file, pcode))
                    else:
                        raise CommandError('Error creating org code={} level={}; '
                                'line={} of file={}; OrganizationLevel requires  '
                                'a parent, but no parent code given'.format(
                                    code, orglevel.name, linenum, input_file,
                                    pcode))

                if verbose:
                    tmp_pcode = '<no parent>'
                    if pcode:
                        tmp_pcode = pcode
                    if created:
                        sys.stderr.write('[VERBOSE] Added Organization '
                                'code={}, level={}, parent={}\n'.format(
                                    code, orglevel.name, tmp_pcode))
                    else:
                        sys.stderr.write('[VERBOSE] Skipping Organization '
                                'code={}, level={}, parent={}; already '
                                'present\n'.format(code, orglevel.name, 
                                    tmp_pcode))

                line = fp.readline()
                linenum += 1
        return
