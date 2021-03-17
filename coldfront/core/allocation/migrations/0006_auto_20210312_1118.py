# Generated by Django 2.2.13 on 2021-03-12 16:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('allocation', '0005_auto_20210311_1318'),
    ]

    operations = [
        migrations.AlterField(
            model_name='allocationuser',
            name='unit',
            field=models.TextField(default='N/A Unit', max_length=20),
        ),
        migrations.AlterField(
            model_name='allocationuser',
            name='usage',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='historicalallocationuser',
            name='unit',
            field=models.TextField(default='N/A Unit', max_length=20),
        ),
        migrations.AlterField(
            model_name='historicalallocationuser',
            name='usage',
            field=models.FloatField(default=0),
        ),
    ]
