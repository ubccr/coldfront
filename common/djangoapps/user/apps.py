from django.apps import AppConfig


class UserConfig(AppConfig):
    name = 'common.djangoapps.user'

    def ready(self):
        import common.djangoapps.user.signals
