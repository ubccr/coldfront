# Generated by Django 2.2.13 on 2021-03-24 16:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('allocation', '0008_auto_20210318_1934'),
    ]

    operations = [
        migrations.AddField(
            model_name='allocationuser',
            name='allocation_group_quota',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalallocationuser',
            name='allocation_group_quota',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
