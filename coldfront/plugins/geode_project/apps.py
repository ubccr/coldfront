from django.apps import AppConfig


class GeodeProjectConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'coldfront.plugins.geode_project'

    def ready(self):
        import coldfront.plugins.geode_project.signals
