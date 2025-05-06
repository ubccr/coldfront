from django import forms
from django.shortcuts import get_object_or_404

from coldfront.core.project.models import Project


class AllocationMoveForm(forms.Form):
    destination_project = forms.ModelChoiceField(queryset=None)
    users = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, request_user, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)
        if request_user == project_obj.pi:
            project_objs = Project.objects.filter(pi=request_user)
        project_objs = Project.objects.filter(status__name="Active").exclude(pk=project_obj.pk)
        self.fields["destination_project"].queryset = project_objs
        user_query_set = (
            project_obj.projectuser_set.select_related("user")
            .filter(
                status__name__in=[
                    "Active",
                ]
            )
            .order_by("user__username")
        )
        user_query_set = user_query_set.exclude(user=project_obj.pi)
        if user_query_set:
            self.fields["users"].choices = (
                (
                    user.user.username,
                    "%s %s (%s)" % (user.user.first_name, user.user.last_name, user.user.username),
                )
                for user in user_query_set
            )
            self.fields[
                "users"
            ].help_text = "<br/>Select users in this allocation to include in the move."
        else:
            self.fields["users"].widget = forms.HiddenInput()
