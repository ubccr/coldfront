# Generated by Django 3.2.5 on 2021-08-17 18:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0012_project_allocation_request_rename_mou'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalsavioprojectallocationrequest',
            name='allocation_type',
            field=models.CharField(choices=[('FCA', 'Faculty Compute Allowance (FCA)'), ('CO', 'Condo Allocation'), ('ICA', 'Instructional Compute Allowance (ICA)'), ('PCA', 'Partner Compute Allowance (PCA)'), ('MOU', 'Memorandum of Understanding (MOU)')], max_length=16),
        ),
        migrations.AlterField(
            model_name='savioprojectallocationrequest',
            name='allocation_type',
            field=models.CharField(choices=[('FCA', 'Faculty Compute Allowance (FCA)'), ('CO', 'Condo Allocation'), ('ICA', 'Instructional Compute Allowance (ICA)'), ('PCA', 'Partner Compute Allowance (PCA)'), ('MOU', 'Memorandum of Understanding (MOU)')], max_length=16),
        ),
    ]