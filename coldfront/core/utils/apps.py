from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = 'coldfront.core.utils'
    verbose_name = 'Coldfront Utils'

    def ready(self):
        import coldfront.core.utils.signals