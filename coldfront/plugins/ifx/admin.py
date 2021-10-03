'''
Admin for ifx
'''
from django.contrib import admin
from ifxuser.admin import UserAdmin
from coldfront.plugins.ifx.models import SuUser, ProjectOrganization

@admin.register(SuUser)
class SuUserAdmin(UserAdmin):
    '''
    Mainly for su-ing
    '''
    change_form_template = "admin/auth/user/change_form.html"
    change_list_template = "admin/auth/user/change_list.html"

@admin.register(ProjectOrganization)
class ProjectOrganizationAdmin(admin.ModelAdmin):
    list_display = ('project', 'organization')
    search_fields = ('project__title', 'organization__name')
    autocomplete_fields = ('project', 'organization')