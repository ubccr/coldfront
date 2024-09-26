from django.apps import AppConfig


class SlateProjectConfig(AppConfig):
    name = 'coldfront.plugins.slate_project'

    def ready(self):
        import coldfront.plugins.slate_project.signals