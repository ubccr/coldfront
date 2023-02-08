# Generated by Django 2.2.4 on 2020-01-04 21:56

from django.db import migrations, models


def add_manual_publication_source(apps, schema_editor):
    PublicationSource = apps.get_model('publication', 'PublicationSource')
    for name, url in [
            ('manual', None),
        ]:
        PublicationSource.objects.get_or_create(name=name, url=url)

class Migration(migrations.Migration):

    dependencies = [
        ('publication', '0003_auto_20200104_1700'),
    ]

    operations = [
        migrations.RunPython(add_manual_publication_source),
    ]
