from django.apps import AppConfig


class QumuloConfig(AppConfig):
    name = "qumulo"

    def ready(self):
        import coldfront.plugins.qumulo.signals
