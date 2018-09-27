from django.apps import AppConfig


class IPAConfig(AppConfig):
    name = 'extra.djangoapps.freeipa'

    def ready(self):
        import extra.djangoapps.freeipa.signals
