from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from django.contrib import admin


@admin.register(BillingActivity)
class BillingActivityAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_project_identifier',
        'get_project_description',
        'identifier',
        'description',
        'is_valid')

    @staticmethod
    @admin.display(
        description='Project Description',
        ordering='billing_project__description')
    def get_project_description(obj):
        return obj.billing_project.description

    @staticmethod
    @admin.display(
        description='Project Identifier',
        ordering='billing_project__identifier')
    def get_project_identifier(obj):
        return obj.billing_project.identifier


@admin.register(BillingProject)
class BillingProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'description')
