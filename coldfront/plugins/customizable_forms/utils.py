import importlib

from django.urls import path

from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.customizable_forms.custom.urls import urlpatterns
from coldfront.plugins.customizable_forms.views import GenericView
from coldfront.plugins.customizable_forms.forms import BaseForm

ADDITIONAL_CUSTOM_FORMS = import_from_settings('ADDITIONAL_CUSTOM_FORMS', [])


def add_additional_forms():
    for additional_form in ADDITIONAL_CUSTOM_FORMS:
        resource_name = additional_form.get('resource_name')
        use_base_form = additional_form.get('use_base_form')
        use_generic_view = additional_form.get('use_generic_view')
        form_module, form_name = additional_form.get('form_path').rsplit('.', 1)
        form_module = importlib.import_module(form_module)
        form_class = getattr(form_module, form_name)
        if use_base_form:
            custom_form = type('CustomForm', (form_class, BaseForm), dict(vars(form_class)))

        view_module, view_name = additional_form.get('view_path').rsplit('.', 1)
        view_module = importlib.import_module(view_module)
        view_class = getattr(view_module, view_name)
        if use_generic_view:
            custom_view = type('CustomForm', (view_class, GenericView), dict(vars(view_class)))

        setattr(custom_view, 'form_class', custom_form)

        urlpatterns.append(
            path(
                f'<int:project_pk>/create/<int:resource_pk>/{resource_name}',
                custom_view.as_view(),
                name=f'{resource_name}-form'
            ),
        )
