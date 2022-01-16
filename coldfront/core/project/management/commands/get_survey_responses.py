from coldfront.core.project.models import Project, SavioProjectAllocationRequest
from django.core.management.base import BaseCommand

import logging
import json
from sys import stdout, stderr
from csv import DictWriter


"""An admin command that downloads survey responses."""


class Command(BaseCommand):

    help = ('Dump Survey Responses to STDOUT')
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        # NOTE(vir): can add date filtering
        parser.add_argument('--format', help='Format to dump survey responses in',
                            type=str, required=True, choices=['json', 'csv'])
        parser.add_argument('--allowance_type', help='Dump responses for Projects with given prefix',
                            type=str, required=False, default='', choices=['ac_', 'co_', 'fc_', 'ic_', 'pc_'])

    def handle(self, *args, **options):
        """ Get all survey responses, and dump to stdout in specified format."""

        format = options['format']
        allowance_type = options['allowance_type']
        writer = getattr(self, f'to_{format}')

        objects = SavioProjectAllocationRequest.objects.filter(
            project__name__istartswith=allowance_type).values_list('survey_answers', flat=True)

        writer(objects, output=options.get('stdout', stdout),
               error=options.get('stderr', stderr))

    @staticmethod
    def to_csv(query_set, output=stdout, error=stderr):
        '''
        write query_set to output and give errors to error.
        does not manage the fds, only writes to them

        Parameters
        ----------
        query_set : QuerySet to write
        output : output fd, defaults to stdout
        error : error fd, defaults to stderr
        '''

        if not query_set:
            error.write('Empty QuerySet, no Surveys matching parameters.')
            return

        try:
            writer = DictWriter(output, query_set[0].keys())
            writer.writeheader()

            for survey in query_set:
                writer.writerow(survey)

        except Exception as e:
            error.write(str(e))

    @staticmethod
    def to_json(query_set, output=stdout, error=stderr):
        '''
        write query_set to output and give errors to error.
        does not manage the fds, only writes to them

        Parameters
        ----------
        query_set : QuerySet to write
        output : output fd, defaults to stdout
        error : error fd, defaults to stderr
        '''

        if not query_set:
            error.write('Empty QuerySet, no Surveys matching parameters.')
            return

        try:
            json_output = json.dumps(list(query_set))
            output.writelines(json_output)
        except Exception as e:
            error.write(str(e))
