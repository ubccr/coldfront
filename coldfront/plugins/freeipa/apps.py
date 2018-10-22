from django.apps import AppConfig


class IPAConfig(AppConfig):
    name = 'coldfront.plugins.freeipa'

    def ready(self):
        import coldfront.plugins.freeipa.signals
