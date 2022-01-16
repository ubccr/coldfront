from django.test import TestCase
from coldfront.core.project.models import *
from django.contrib.auth.models import User
from django.core.management import call_command


from coldfront.core.project.models import SavioProjectAllocationRequest, Project, ProjectAllocationRequestStatusChoice, ProjectStatusChoice, FieldOfScience, User

from io import StringIO
import sys
import json
from csv import DictReader


class TestGetSurveyResponses(TestCase):
    """
    Base Class for testing
    """

    def setUp(self):
        # create dummy survey responses
        fixtures = []
        filtered_fixtures = []

        # dummy params
        allocation_type = SavioProjectAllocationRequest.FCA
        pool = False

        for index in range(5):
            pi = User.objects.create(
                username=f'test_user{index}', first_name='Test', last_name='User', is_superuser=True)
            project_prefix = 'fc_' if index % 2 else ''
            project = Project.objects.create(name=f'{project_prefix}test_project{index}', status=ProjectStatusChoice.objects.create(
                name='Active'), field_of_science=FieldOfScience.objects.create())
            status = ProjectAllocationRequestStatusChoice.objects.create(
                name='TEST')

            survey_answers = {'a': f'answera_{index}', 'b': f'answerb_{index}'}

            kwargs = {
                'allocation_type': allocation_type,
                'pi': pi,
                'project': project,
                'pool': pool,
                'survey_answers': survey_answers,
                'status': status,
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
            self.assertDictEqual(
                item, self.filtered_fixtures[index].survey_answers)

        err.seek(0)
        self.assertEqual(err.read(), '')
