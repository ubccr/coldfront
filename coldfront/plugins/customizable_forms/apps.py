from django.apps import AppConfig


class CustomizableFormsConfig(AppConfig):
    name = 'coldfront.plugins.customizable_forms'

    def ready(self):
        from coldfront.plugins.customizable_forms.utils import add_additional_forms
        add_additional_forms()
