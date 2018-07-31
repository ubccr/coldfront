from django.apps import AppConfig


class SlurmConfig(AppConfig):
    name = 'extra.djangoapps.slurm'

    def ready(self):
        import extra.djangoapps.slurm.signals
