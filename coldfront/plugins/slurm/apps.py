from django.apps import AppConfig


class SlurmConfig(AppConfig):
    name = 'coldfront.plugins.slurm'


    def ready(self):
        import coldfront.plugins.slurm.signals
