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
        module_name = additional_form.get('module_name')
        view_path = additional_form.get('view_path')
        if not view_path:
            view_path = 'views'
        form_path = additional_form.get('form_path')
        if not form_path:
            form_path = 'forms'

        form_class_name = additional_form.get('form_class')
        view_class_name = additional_form.get('view_class')
        
        try:
            form_module = importlib.import_module(f'{module_name}.{form_path}')
            view_module = importlib.import_module(f'{module_name}.{view_path}')
        except ModuleNotFoundError:
            base_path = 'coldfront.plugins'
            form_module = importlib.import_module(f'{base_path}.{module_name}.{form_path}')
            view_module = importlib.import_module(f'{base_path}.{module_name}.{view_path}')

        use_base_form = additional_form.get('use_base_form')
        use_generic_view = additional_form.get('use_generic_view')

        form_class = getattr(form_module, form_class_name)
        if use_base_form:
            custom_form = type('CustomForm', (form_class, BaseForm), dict(vars(form_class)))

        view_class = getattr(view_module, view_class_name)
        if use_generic_view:
            custom_view = type('CustomForm', (view_class, GenericView), dict(vars(view_class)))

        setattr(custom_view, 'form_class', custom_form)

        resource_name = additional_form.get('resource_name')
        resource_name = re.sub('[^A-Za-z0-9]+', '', resource_name)
        urlpatterns.append(
            path(
                f'project/<int:project_pk>/create/<int:resource_pk>/{resource_name}',
                custom_view.as_view(),
                name=f'{resource_name.lower()}-form'
            ),
        )

    urlpatterns.append(path(
            'project/<int:project_pk>/create/<int:resource_pk>/<str:resource_name>',
            GenericView.as_view(),
            name='resource-form'
        )
    )
