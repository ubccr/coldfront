from django.apps import AppConfig


class AccountConfig(AppConfig):
    name = 'coldfront.core.account'
    label = 'custom_account'

    def ready(self):
        pass
