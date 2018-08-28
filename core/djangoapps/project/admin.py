import textwrap

from admin_comments.admin import CommentInline
from django.contrib import admin

from core.djangoapps.project.models import (Project, ProjectStatusChoice,
                                            ProjectUser, ProjectUserRoleChoice,
                                            ProjectUserStatusChoice, ProjectReview)


from simple_history.admin import SimpleHistoryAdmin

@admin.register(ProjectStatusChoice)
class ProjectStatusChoiceAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(ProjectUserRoleChoice)
class ProjectUserRoleChoiceAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(ProjectUserStatusChoice)
class ProjectUserStatusChoiceAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(ProjectUser)
class ProjectUserAdmin(SimpleHistoryAdmin):
    fields_change = ('user', 'project', 'role', 'status', 'created', 'modified', )
    readonly_fields_change = ('user', 'project', 'created', 'modified', )
    list_display = ('pk', 'project_title', 'PI', 'User', 'role', 'status',
                    'created', 'modified',)
    list_filter = ('role', 'status')
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    inlines_change = [CommentInline, ]
    raw_id_fields = ('user', 'project')

    def project_title(self, obj):
        return textwrap.shorten(obj.project.title, width=50)

    def PI(self, obj):
        return '{} {} ({})'.format(obj.project.pi.first_name, obj.project.pi.last_name, obj.project.pi.username)

    def User(self, obj):
        return '{} {} ({})'.format(obj.user.first_name, obj.user.last_name, obj.user.username)

    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        else:
            return self.fields_change

    def get_readonly_fields(self, request, obj):
        if obj is None:
            # We are adding an object
            return super().get_readonly_fields(request)
        else:
            return self.readonly_fields_change

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            # We are adding an object
            return super().get_inline_instances(request)
        else:
            return [inline(self.model, self.admin_site) for inline in self.inlines_change]


class ProjectUserInline(admin.TabularInline):
    model = ProjectUser
    fields = ['user', 'project', 'role', 'status', 'enable_notifications', ]
    readonly_fields = ['user', 'project', ]
    extra = 0

    def has_add_permission(self, request):
        return False


@admin.register(Project)
class ProjectAdmin(SimpleHistoryAdmin):
    fields_change = ('title', 'pi', 'description', 'status', 'project_requires_review', 'force_project_review', 'created', 'modified', )
    readonly_fields_change = ('pi', 'created', 'modified', )
    list_display = ('pk', 'title', 'PI', 'created', 'modified', 'status')
    search_fields = ['pi__username', 'projectuser__user__username',
                     'projectuser__user__last_name', 'projectuser__user__last_name', 'title']
    list_filter = ('status', 'force_project_review')
    inlines_change = [ProjectUserInline, CommentInline]

    def PI(self, obj):
        return '{} {} ({})'.format(obj.pi.first_name, obj.pi.last_name, obj.pi.username)

    def get_fields(self, request, obj):
        if obj is None:
            return super().get_fields(request)
        else:
            return self.fields_change

    def get_readonly_fields(self, request, obj):
        if obj is None:
            # We are adding an object
            return super().get_readonly_fields(request)
        else:
            return self.readonly_fields_change

    def get_inline_instances(self, request, obj=None):
        if obj is None:
            # We are adding an object
            return super().get_inline_instances(request)
        else:
            return [inline(self.model, self.admin_site) for inline in self.inlines_change]


@admin.register(ProjectReview)
class ProjectReviewAdmin(SimpleHistoryAdmin):
    list_display = ('pk', 'project', 'reason_for_not_updating_project', 'created', 'status')
    list_filter = ('status', )
