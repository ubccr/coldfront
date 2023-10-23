from django.apps import AppConfig


class CheckInactiveUsersConfig(AppConfig):
    name = 'coldfront.plugins.check_inactive_users'

    def ready(self):
        import coldfront.plugins.check_inactive_users.signals
