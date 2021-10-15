from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple

from coldfront.core.organization.models import (
    Organization, OrganizationLevel, Directory2Organization)

from coldfront.core.user.models import UserProfile
from coldfront.core.project.models import Project

@admin.register(OrganizationLevel)
class OrganizationLevelAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'level',
        'parent',
    )
    search_fields = ['name', 'level']

class OrganizationAdminForm(forms.ModelForm):
    """Custom form to expose users/projects on Organization admin page.

    Even though the manytomany was defined on UserProfile and
    Projects.  See 
    https://stackoverflow.com/questions/9879687/adding-a-manytomanywidget-to-the-reverse-of-a-manytomanyfield-in-the-django-admi/13189954
    and https://gist.github.com/Grokzen/a64321dd69339c42a184
    """
    # Define custom fields for users and projects
    users = forms.ModelMultipleChoiceField(
        queryset = UserProfile.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name='Users',
            is_stacked=False,
        )
    )
    projects = forms.ModelMultipleChoiceField(
        queryset = Project.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name='Projects',
            is_stacked=False,
        )
    )

    class Meta:
        model = Organization
        fields = [ 'code', 'parent', 'organization_level',
            'shortname', 'longname', 'users', 'projects' ]

    def __init__(self, *args, **kwargs):
        """Populate users/projects with current values"""
        super(OrganizationAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['users'].initial = self.instance.users.all()
            self.fields['projects'].initial = self.instance.projects.all()

    def save(self, commit=True):
        """Save the updated users/projects fields along with rest of object"""
        organization = super(OrganizationAdminForm, self).save(commit=False)
        if commit:
            organization.save()
        if organization.pk:
            # Update the users m2m relationship
            oldusers_set = set(organization.users.all())
            newusers_set = set(self.cleaned_data['users'])
            users2add = list(newusers_set - oldusers_set)
            users2del = list(oldusers_set - newusers_set)
            for userprof in users2del:
                organization.users.remove(userprof)
            for userprof in users2add:
                organization.users.add(userprof)

            # Update the projects m2m relationship
            oldprojects_set = set(organization.projects.all())
            newprojects_set = set(self.cleaned_data['projects'])
            projects2add = list(newprojects_set - oldprojects_set)
            projects2del = list(oldprojects_set - newprojects_set)
            for projectprof in projects2del:
                organization.projects.remove(projectprof)
            for projectprof in projects2add:
                organization.projects.add(projectprof)
            self.save_m2m()
        return organization

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        'fullcode',
        'parent',
        'organization_level',
        'shortname',
        'longname',
    )
    fields_change = (
        'fullcode',
        'parent',
        'organization_level',
        'shortname',
        'longname',
    )
    search_fields = ['code',]
    form = OrganizationAdminForm


@admin.register(Directory2Organization)
class Directory2OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        'organization',
        'directory_string',
    )
    search_fields = ['directory_string', 'organization']
