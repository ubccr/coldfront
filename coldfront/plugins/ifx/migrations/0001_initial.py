# Generated by Django 2.2.18 on 2021-05-03 20:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('allocation', '0003_auto_20191018_1049'),
        ('resource', '0002_auto_20191017_1141'),
        ('ifxbilling', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductResource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ifxbilling.Product')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='resource.Resource')),
            ],
        ),
        migrations.CreateModel(
            name='AllocationProductUsage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('allocation', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='allocation.Allocation')),
                ('product_usage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ifxbilling.ProductUsage')),
            ],
        ),
    ]