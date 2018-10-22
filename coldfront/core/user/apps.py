from django.apps import AppConfig


class UserConfig(AppConfig):
    name = 'coldfront.core.user'

    def ready(self):
        import coldfront.core.user.signals
