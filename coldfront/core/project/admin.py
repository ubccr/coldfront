import textwrap

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from coldfront.core.project.models import (Project, ProjectAdminComment,
                                            ProjectReview, ProjectStatusChoice,
                                            ProjectUser, ProjectUserMessage,
                                            ProjectUserRoleChoice,
                                            ProjectUserStatusChoice)


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
    list_display = ('pk', 'project_title', 'User', 'role', 'status', 'created',
                    'modified',)
    list_filter = ('role', 'status')
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    raw_id_fields = ('user', 'project')

    def project_title(self, obj):
        return textwrap.shorten(obj.project.title, width=50)

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
            return []
            # return [inline(self.model, self.admin_site) for inline in self.inlines_change]


class ProjectUserInline(admin.TabularInline):
    model = ProjectUser
    fields = ['user', 'project', 'role', 'status', 'enable_notifications', ]
    readonly_fields = ['user', 'project', ]
    extra = 0


class ProjectAdminCommentInline(admin.TabularInline):
    model = ProjectAdminComment
    extra = 0
    fields = ('comment', 'author', 'created'),
    readonly_fields = ('author', 'created')


class ProjectUserMessageInline(admin.TabularInline):
    model = ProjectUserMessage
    extra = 0
    fields = ('message', 'author', 'created'),
    readonly_fields = ('author', 'created')


@admin.register(Project)
class ProjectAdmin(SimpleHistoryAdmin):
    fields_change = ('title', 'description', 'status', 'requires_review', 'force_review', 'created', 'modified', )
    readonly_fields_change = ('created', 'modified', )
    list_display = ('pk', 'title', 'PIs', 'created', 'modified', 'status')
    search_fields = ['projectuser__user__username',
                     'projectuser__user__last_name', 'projectuser__user__last_name', 'title']
    list_filter = ('status', 'force_review')
    inlines = [ProjectUserInline, ProjectAdminCommentInline, ProjectUserMessageInline]
    raw_id_fields = []

    def PIs(self, obj):
        pi_users = obj.pis()
        return '\n'.join([
            '{} {} ({})'.format(
                pi_user.first_name, pi_user.last_name, pi_user.username)
            for pi_user in pi_users])

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
            return []
        else:
            return super().get_inline_instances(request)

    def save_formset(self, request, form, formset, change):
        if formset.model in [ProjectAdminComment, ProjectUserMessage]:
            instances = formset.save(commit=False)
            for instance in instances:
                instance.author = request.user
                instance.save()
        else:
            formset.save()


@admin.register(ProjectReview)
class ProjectReviewAdmin(SimpleHistoryAdmin):
    list_display = ('pk', 'project', 'PIs', 'reason_for_not_updating_project', 'created', 'status')
    list_filter = ('status', )

    def PIs(self, obj):
        pi_users = obj.pis()
        return '\n'.join([
            '{} {} ({})'.format(
                pi_user.first_name, pi_user.last_name, pi_user.username)
            for pi_user in pi_users])
