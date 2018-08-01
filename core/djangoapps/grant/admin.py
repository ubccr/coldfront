from django.contrib import admin

from core.djangoapps.grant.models import Grant, GrantFundingAgency


@admin.register(GrantFundingAgency)
class GrantFundingAgencyChoiceAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(Grant)
class GrantAdmin(admin.ModelAdmin):
    list_display = ['title', 'Project_PI', 'role', 'grant_pi_full_name', 'funding_agency', 'status', 'project_end']
    list_filter = ('funding_agency', 'role', 'status', 'project_end' )
    search_fields = ['project__title',
        'project__pi__username',
        'project__pi__first_name',
        'project__pi__last_name',
        'funding_agency__name', 'grant_pi_full_name']

    def Project_PI(self, obj):
        return '{} {} ({})'.format(obj.project.pi.first_name, obj.project.pi.last_name, obj.project.pi.username)
