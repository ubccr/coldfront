import re
import importlib

from django.urls import path

from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.customizable_forms.urls import urlpatterns
from coldfront.plugins.customizable_forms.views import GenericView
from coldfront.plugins.customizable_forms.forms import BaseForm

ADDITIONAL_CUSTOM_FORMS = import_from_settings('ADDITIONAL_CUSTOM_FORMS', [])


def add_additional_forms():
    for additional_form in ADDITIONAL_CUSTOM_FORMS:
        view_module = additional_form.get('view_module')
        view_module = importlib.import_module(view_module)
        view_class = additional_form.get('view_class')
        view_class = getattr(view_module, view_class)

        resource_name = additional_form.get('resource_name')
        resource_name = re.sub('[^A-Za-z0-9]+', '', resource_name)
        urlpatterns.append(
            path(
                f'project/<int:project_pk>/create/<int:resource_pk>/{resource_name}',
                view_class.as_view(),
                name=f'{resource_name.lower()}-form'
            ),
        )

    urlpatterns.append(path(
            'project/<int:project_pk>/create/<int:resource_pk>/<str:resource_name>',
            GenericView.as_view(),
            name='resource-form'
        )
    )
