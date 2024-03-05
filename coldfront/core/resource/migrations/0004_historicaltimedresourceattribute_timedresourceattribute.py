# Generated by Django 3.2.5 on 2023-08-03 19:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('resource', '0003_add_resource_is_unique_per_project'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalTimedResourceAttribute',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('value', models.TextField()),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('resource', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='resource.resource')),
                ('resource_attribute_type', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='resource.resourceattributetype')),
            ],
            options={
                'verbose_name': 'historical timed resource attribute',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='TimedResourceAttribute',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('value', models.TextField()),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='resource.resource')),
                ('resource_attribute_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='resource.resourceattributetype')),
            ],
            options={
                'unique_together': {('resource_attribute_type', 'resource', 'start_date', 'end_date')},
            },
        ),
    ]