from django.apps import AppConfig


class QumuloConfig(AppConfig):
    name = "coldfront_plugin_qumulo"

    def ready(self):
        import coldfront_plugin_qumulo.signals
