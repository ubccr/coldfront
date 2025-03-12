import importlib
from django.core.management.base import BaseCommand
from simple_history.utils import get_history_manager_for_model


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--module',
            help='Primary module to backfill change reasons into, i.e. allocation',
            required=True
        )

        parser.add_argument(
            '--model',
            help='Model to backfill change reasons into, i.e. AllocationAttribute',
            required=True
        )

        parser.add_argument(
            '--replace',
            help='Replace current existing change reasons',
            action='store_true'
        )

    def handle(self, *args, **options):
        module = options.get('module')
        model = options.get('model')
        module_path = f'coldfront.core.{module}.models'
        module = importlib.import_module(module_path)
        model_objs = getattr(module, model).objects.all()
        for model_obj in model_objs:
            history = get_history_manager_for_model(model_obj)
            records = history.all()
            for record in records:
                if record.history_change_reason and not options.get('replace'):
                    continue

                prev_record = record.prev_record
                if prev_record is None:
                    record.history_change_reason = "Created"
                    record.save()
                    continue

                record_delta = record.diff_against(prev_record)
                changes = []
                for change in record_delta.changes:
                    changes.append(change.field)

                record.history_change_reason = f"Fields changed: {', '.join(changes)}"
                record.save()