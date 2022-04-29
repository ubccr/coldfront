from django.contrib import admin

from coldfront.core.statistics.models import CPU
from coldfront.core.statistics.models import Job
from coldfront.core.statistics.models import Node
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction


@admin.register(ProjectTransaction)
class ProjectTransactionAdmin(admin.ModelAdmin):
    list_display = ('date_time', 'project', 'allocation', )

    search_fields = ('project__name',)


@admin.register(ProjectUserTransaction)
class ProjectUserTransactionAdmin(admin.ModelAdmin):
    list_display = ('date_time', 'get_project', 'get_user', 'allocation', )
    search_fields = ('project_user__project__name',
                     'project_user__user__username')

    def get_project(self, obj):
        return obj.project_user.project
    get_project.short_description = 'Project'
    get_project.admin_order_field = 'project_user__project'

    def get_user(self, obj):
        return obj.project_user.user
    get_user.short_description = 'User'
    get_user.admin_order_field = 'project_user__user'


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('jobslurmid', 'user', 'project', 'jobstatus', 'partition')
    search_fields = ['jobslurmid', 'userid__username', 'accountid__name', 'jobstatus', 'partition']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def user(self, obj):
        return obj.userid.username

    def project(self, obj):
        return obj.accountid.name


admin.register(CPU)
admin.register(Node)
