from django.apps import AppConfig


class UserConfig(AppConfig):
    name = 'coldfront.core.user'

    def ready(self):
        pass
