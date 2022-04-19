from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple

from coldfront.core.organization.models import (
        Organization, 
        OrganizationLevel, 
        OrganizationProject, 
        OrganizationUser, 
        Directory2Organization,
    )

from coldfront.core.user.models import UserProfile
from coldfront.core.project.models import Project

@admin.register(OrganizationLevel)
class OrganizationLevelAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'level',
        'parent',
        'export_to_xdmod',
    )
    search_fields = ['name', 'level']
#end: class OrganizationLevelAdmin

class OrganizationProjectInline(admin.TabularInline):
    model = OrganizationProject
    extra = 1

    # Limit to Organizations with is_selectable_for_project
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(OrganizationProjectInline, self).formfield_for_foreignkey(
                db_field, request, **kwargs)
        if db_field.name == 'organization':
            field.queryset = field.queryset.filter(
                    is_selectable_for_project=True)
        return field
#end: class OrganizationProjectInline

class OrganizationUserInline(admin.TabularInline):
    model = OrganizationUser
    extra = 1

    # Limit to Organizations with is_selectable_for_project
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(OrganizationUserInline, self).formfield_for_foreignkey(
                db_field, request, **kwargs)
        if db_field.name == 'organization':
            field.queryset = field.queryset.filter(
                    is_selectable_for_project=True)
        return field
#end: class OrganizationUserInline

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        'fullcode',
        'parent',
        'organization_level',
        'shortname',
        'longname',
        'is_selectable_for_user',
        'is_selectable_for_project',
    )
    fields_change = (
        'fullcode',
        'parent',
        'organization_level',
        'shortname',
        'longname',
        'is_selectable_for_user',
        'is_selectable_for_project',
    )
    search_fields = ['code',]
    list_filter = ( 
            'organization_level', 
            'is_selectable_for_user',
            'is_selectable_for_project',
            )
    inlines = (
            OrganizationProjectInline,
            OrganizationUserInline,
        )

    # Only enable project/user inlines if Org is selectable for proj/user
    # This is proviing problematic.  Have found some 'recipes', e.g.
    # https://stackoverflow.com/questions/25772856/disable-hide-unnecessary-inline-forms-in-django-admin
    # https://stackoverflow.com/questions/5411565/making-inlines-conditional-in-the-django-admin
    # These sort-of work, in that Inlines only appear is is_selectable set,
    # but get wierd errors:
    # Hidden field errors: TOTAL_FORMS, INITIAL_FORMS field is required
    # ManagementForm data is missing/tampered with
    # when change an is_selectable from false to true
    #
    # Opting instead to always display the inlines, but set max_num to 0 if
    # not selectable.  This avoids errors, show any existing members,but makes
    # it difficult to add new members.
    def get_inline_instances(self, request, obj=None):
        inlines = list(self.inlines)
        inline_instances = []
        for inline_class in inlines:
            inline = inline_class(self.model, self.admin_site)
            if request:
                if not( inline.has_add_permission(request, obj) or
                        inline.has_change_permission(request) or
                        inline.has_delete_permission(request)):
                    continue
                if not inline.has_add_permission(request, obj):
                    inline.max_num = 0
            #end: if request
            if isinstance(inline, OrganizationProjectInline):
                if obj is not None and not obj.is_selectable_for_project:
                    inline.max_num = 0
            if isinstance(inline, OrganizationUserInline):
                if obj is not None and not obj.is_selectable_for_user:
                    inline.max_num = 0
            inline_instances.append(inline)
        #end: for inline_class
        return inline_instances

#end: class OrganizationAdmin


@admin.register(Directory2Organization)
class Directory2OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        'organization',
        'directory_string',
    )
#end: class Directory2OrganizationAdmin

