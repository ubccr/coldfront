from coldfront.core.field_of_science.models import FieldOfScience

from coldfront.plugins.qumulo.forms.ProjectCreateForm import ProjectCreateForm
from coldfront.plugins.qumulo.tests.utils.mock_data import build_models
from coldfront.plugins.qumulo.views.project_views import PluginProjectCreateView

from django.test import TestCase
from django.urls.exceptions import NoReverseMatch
from unittest.mock import patch, MagicMock


@patch("coldfront.plugins.qumulo.validators.ActiveDirectoryAPI")
class ProjectCreateViewTests(TestCase):
    def setUp(self):
        self.testPI = "sleong"
        build_data = build_models()
        self.fieldOfScience = FieldOfScience.objects.create(description="Bummerology")

    def test_created_project_has_pi(self, mock_ActiveDirectoryAPI: MagicMock):
        valid_data = {
            "title": "project-sleong",
            "pi": self.testPI,
            "description": "This is the description for the project",
            "field_of_science": self.fieldOfScience.id,
        }
        form = ProjectCreateForm(data=valid_data, user_id="admin")
        form.is_valid()
        view = PluginProjectCreateView()
        try:
            view.form_valid(form)
        except NoReverseMatch:
            pass
        self.assertEqual(view.project.pi.username, self.testPI)
