# Generated by Django 2.2.13 on 2021-03-18 23:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('allocation', '0007_auto_20210318_1826'),
    ]

    operations = [
        migrations.AlterField(
            model_name='allocationuser',
            name='allocation_group_usage_bytes',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='historicalallocationuser',
            name='allocation_group_usage_bytes',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
