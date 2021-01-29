from django.apps import AppConfig


class AllocationConfig(AppConfig):
    name = 'allocation'

    def ready(self):
        import coldfront.core.allocation.signals
