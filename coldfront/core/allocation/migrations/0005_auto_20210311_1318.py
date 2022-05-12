# Generated by Django 2.2.13 on 2021-03-11 18:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('allocation', '0004_auto_20210309_1142'),
    ]

    operations = [
        migrations.AddField(
            model_name='allocationuser',
            name='usage_bytes',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalallocationuser',
            name='usage_bytes',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='allocationuser',
            name='unit',
            field=models.TextField(default='bytes', max_length=20),
        ),
        migrations.AlterField(
            model_name='allocationuser',
            name='usage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AlterField(
            model_name='historicalallocationuser',
            name='unit',
            field=models.TextField(default='bytes', max_length=20),
        ),
        migrations.AlterField(
            model_name='historicalallocationuser',
            name='usage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
    ]