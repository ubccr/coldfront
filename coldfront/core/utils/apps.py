from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = 'coldfront.core.utils'

    def ready(self):
        import coldfront.core.utils.flag_conditions
