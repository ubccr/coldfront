from django.apps import AppConfig


class SocialAccountConfig(AppConfig):
    name = 'coldfront.core.socialaccount'
    label = 'custom_socialaccount'

    def ready(self):
        import coldfront.core.socialaccount.signals
