from django.apps import AppConfig


class AutoComputeAllocationConfig(AppConfig):
    name = 'coldfront.plugins.auto_compute_allocation'


    def ready(self):
        import coldfront.plugins.auto_compute_allocation.signals
