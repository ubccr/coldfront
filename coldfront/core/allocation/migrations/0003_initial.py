# Generated by Django 4.2.11 on 2025-01-31 16:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("resource", "0001_initial"),
        ("allocation", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="allocation",
            name="resources",
            field=models.ManyToManyField(to="resource.resource"),
        ),
        migrations.AddField(
            model_name="allocation",
            name="status",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="allocation.allocationstatuschoice",
                verbose_name="Status",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="allocationuser",
            unique_together={("user", "allocation")},
        ),
    ]
