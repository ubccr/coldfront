from django.dispatch import receiver
from simple_history.signals import post_create_historical_record
from simple_history.utils import update_change_reason


@receiver(post_create_historical_record)
def save_historical_change_reason(sender, instance, **kwargs):
    full_history = instance.history.all()
    if len(full_history) < 2:
        update_change_reason(instance, 'Created')
        return

    new_history, prev_history = full_history[:2]
    history_delta = new_history.diff_against(prev_history)
    changes = []
    for change in history_delta.changes:
        changes.append(change.field)

    update_change_reason(instance, f"Fields changed: {', '.join(changes)}")
