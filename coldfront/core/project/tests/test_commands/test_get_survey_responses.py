from django.test import TestCase
from coldfront.core.project.models import *
from django.contrib.auth.models import User
from django.core.management import call_command


from coldfront.core.project.models import (SavioProjectAllocationRequest,
                                           Project,
                                           ProjectAllocationRequestStatusChoice,
                                           ProjectStatusChoice,
                                           User)

from io import StringIO
import sys
import json
import os
from csv import DictReader


class TestGetSurveyResponses(TestCase):
    """
    Base Class for testing
    """

    def setUp(self):
        # run setup commands
        out, err = StringIO(), StringIO()
        commands = [
            'add_default_project_choices',
            'import_field_of_science_data'
        ]
        sys.stdout = open(os.devnull, 'w')
        for command in commands:
            call_command(command, stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        # create dummy survey responses
        fixtures = []
        filtered_fixtures = []

        # dummy params
        allocation_type = SavioProjectAllocationRequest.FCA
        pool = False

        for index in range(5):
            pi = User.objects.create(
                username=f'test_user{index}', first_name='Test', last_name='User',
                is_superuser=True)

            project_status = ProjectStatusChoice.objects.get(name='Active')
            allocation_status = ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')

            project_prefix = 'fc_' if index % 2 else ''
            project = Project.objects.create(name=f'{project_prefix}test_project{index}',
                                             status=project_status)

            survey_answers = {
                'scope_and_intent': 'sample scope',
                'computational_aspects': 'sample aspects',
            }

            kwargs = {
                'allocation_type': allocation_type,
                'pi': pi,
                'project': project,
                'pool': pool,
                'survey_answers': survey_answers,
                'status': allocation_status,
                'requester': pi
            }

            fixture = SavioProjectAllocationRequest.objects.create(**kwargs)
            fixtures.append(fixture)

            if index % 2:
                filtered_fixtures.append(fixture)

        self.fixtures = fixtures
        self.filtered_fixtures = filtered_fixtures

    def test_get_survey_responses_json(self):
        out, err = StringIO(''), StringIO('')
        call_command('get_survey_responses', stdout=out,
                     stderr=err, format='json')
        sys.stdout = sys.__stdout__

        out.seek(0)
        output = json.loads(''.join(out.readlines()))
        for index, item in enumerate(output):
            project_name = item.pop('project_name')
            project_title = item.pop('project_title')
            self.assertEquals(project_name, self.fixtures[index].project.name)
            self.assertEquals(project_title, self.fixtures[index].project.title)
            self.assertDictEqual(item, self.fixtures[index].survey_answers)

        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_get_survey_responses_csv(self):
        out, err = StringIO(''), StringIO('')
        call_command('get_survey_responses', stdout=out,
                     stderr=err, format='csv')
        sys.stdout = sys.__stdout__

        out.seek(0)
        reader = DictReader(out.readlines())
        for index, item in enumerate(reader):
            project_name = item.pop('project_name')
            project_title = item.pop('project_title')
            self.assertEquals(project_name, self.fixtures[index].project.name)
            self.assertEquals(project_title, self.fixtures[index].project.title)
            self.assertDictEqual(item, self.fixtures[index].survey_answers)

        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_get_survey_responses_allowance_type(self):
        out, err = StringIO(''), StringIO('')
        call_command('get_survey_responses', stdout=out,
                     stderr=err, format='csv', allowance_type='fc_')
        sys.stdout = sys.__stdout__

        out.seek(0)
        reader = DictReader(out.readlines())
        for index, item in enumerate(reader):
            project_name = item.pop('project_name')
            project_title = item.pop('project_title')
            self.assertEquals(project_name, self.filtered_fixtures[index].project.name)
            self.assertEquals(project_title, self.filtered_fixtures[index].project.title)
            self.assertDictEqual(item, self.filtered_fixtures[index].survey_answers)

        err.seek(0)
        self.assertEqual(err.read(), '')