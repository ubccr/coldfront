# Generated by Django 3.1.7 on 2021-03-21 04:10

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0006_projectuserjoinrequest'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicalproject',
            name='joins_require_approval',
        ),
        migrations.RemoveField(
            model_name='project',
            name='joins_require_approval',
        ),
        migrations.AddField(
            model_name='historicalproject',
            name='joins_auto_approval_delay',
            field=models.DurationField(default=datetime.timedelta(seconds=21600)),
        ),
        migrations.AddField(
            model_name='project',
            name='joins_auto_approval_delay',
            field=models.DurationField(default=datetime.timedelta(seconds=21600)),
        ),
    ]