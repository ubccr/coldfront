from django.contrib import admin

from coldfront.core.statistics.models import CPU
from coldfront.core.statistics.models import Job
from coldfront.core.statistics.models import Node
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction


class ProjectTransactionAdmin(admin.ModelAdmin):
    list_display = ('date_time', 'project', 'allocation', )


class ProjectUserTransactionAdmin(admin.ModelAdmin):
    list_display = ('date_time', 'get_project', 'get_user', 'allocation', )

    def get_project(self, obj):
        return obj.project_user.project
    get_project.short_description = 'Project'
    get_project.admin_order_field = 'project_user__project'

    def get_user(self, obj):
        return obj.project_user.user
    get_user.short_description = 'User'
    get_user.admin_order_field = 'project_user__user'


admin.register(CPU)
admin.register(Job)
admin.register(Node)
admin.site.register(ProjectTransaction, ProjectTransactionAdmin)
admin.site.register(ProjectUserTransaction, ProjectUserTransactionAdmin)
