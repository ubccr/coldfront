from django.apps import AppConfig


class QumuloConfig(AppConfig):
    name = "coldfront.plugins.qumulo"

    def ready(self):
        import coldfront.plugins.qumulo.signals
