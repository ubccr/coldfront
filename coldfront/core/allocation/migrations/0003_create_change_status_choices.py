from django.db import migrations


def create_change_status_choices(apps, schema_editor):
    """Ensure that AllocationChangeStatusChoice has 'Pending', 'Approved', 'Denied'."""
    AllocationChangeStatusChoice = apps.get_model(
        "allocation", "AllocationChangeStatusChoice"
    )
    for choice in ("Pending", "Approved", "Denied"):
        AllocationChangeStatusChoice.objects.get_or_create(name=choice)


class Migration(migrations.Migration):
    dependencies = [
        ("allocation", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(create_change_status_choices),
    ]
