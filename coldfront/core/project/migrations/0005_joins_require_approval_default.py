# Generated by Django 3.1.7 on 2021-03-14 17:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0004_add_joins_require_approval'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalproject',
            name='joins_require_approval',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='joins_require_approval',
            field=models.BooleanField(default=True),
        ),
    ]