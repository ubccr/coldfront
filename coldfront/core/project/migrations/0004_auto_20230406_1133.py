# Generated by Django 3.2.17 on 2023-04-06 15:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0003_auto_20221013_1215'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectstatuschoice',
            name='name',
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name='projectuserrolechoice',
            name='name',
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name='projectuserstatuschoice',
            name='name',
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
