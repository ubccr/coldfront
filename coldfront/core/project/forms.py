# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime

from django import forms
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404

from coldfront.core.project.models import Project, ProjectAttribute, ProjectReview, ProjectUserRoleChoice
from coldfront.core.utils.common import import_from_settings

EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL = import_from_settings("EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL")
EMAIL_ADMIN_LIST = import_from_settings("EMAIL_ADMIN_LIST", [])
EMAIL_DIRECTOR_EMAIL_ADDRESS = import_from_settings("EMAIL_DIRECTOR_EMAIL_ADDRESS", "")


class ProjectSearchForm(forms.Form):
    """Search form for the Project list page."""

    LAST_NAME = "Last Name"
    USERNAME = "Username"
    FIELD_OF_SCIENCE = "Field of Science"

    last_name = forms.CharField(label=LAST_NAME, max_length=100, required=False)
    username = forms.CharField(label=USERNAME, max_length=100, required=False)
    field_of_science = forms.CharField(label=FIELD_OF_SCIENCE, max_length=100, required=False)
    show_all_projects = forms.BooleanField(initial=False, required=False)


class ProjectAddUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=150, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    source = forms.CharField(max_length=16, disabled=True)
    role = forms.ModelChoiceField(queryset=ProjectUserRoleChoice.objects.all(), empty_label=None)
    selected = forms.BooleanField(initial=False, required=False)


class ProjectAddUsersToAllocationForm(forms.Form):
    allocation = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={"checked": "checked"}), required=False
    )

    def __init__(self, request_user, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)

        allocation_query_set = project_obj.allocation_set.filter(
            resources__is_allocatable=True,
            is_locked=False,
            status__name__in=["Active", "New", "Renewal Requested", "Payment Pending", "Payment Requested", "Paid"],
        )
        allocation_choices = [
            (
                allocation.id,
                "%s (%s) %s"
                % (
                    allocation.get_parent_resource.name,
                    allocation.get_parent_resource.resource_type.name,
                    allocation.description if allocation.description else "",
                ),
            )
            for allocation in allocation_query_set
        ]
        allocation_choices_sorted = []
        allocation_choices_sorted = sorted(allocation_choices, key=lambda x: x[1][0].lower())
        allocation_choices.insert(0, ("__select_all__", "Select All"))
        if allocation_query_set:
            self.fields["allocation"].choices = allocation_choices_sorted
            self.fields["allocation"].help_text = "<br/>Select allocations to add selected users to."
        else:
            self.fields["allocation"].widget = forms.HiddenInput()


class ProjectRemoveUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=150, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    role = forms.CharField(max_length=30, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class ProjectUserUpdateForm(forms.Form):
    role = forms.ModelChoiceField(queryset=ProjectUserRoleChoice.objects.all(), empty_label=None)
    enable_notifications = forms.BooleanField(initial=False, required=False)


class ProjectReviewForm(forms.Form):
    reason = forms.CharField(
        label="Reason for not updating project information",
        widget=forms.Textarea(
            attrs={
                "placeholder": "If you have no new information to provide, you are required to provide a statement explaining this in this box. Thank you!"
            }
        ),
        required=False,
    )
    acknowledgement = forms.BooleanField(
        label="By checking this box I acknowledge that I have updated my project to the best of my knowledge",
        initial=False,
        required=True,
    )

    def __init__(self, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)
        now = datetime.datetime.now(datetime.timezone.utc)

        if project_obj.grant_set.exists():
            latest_grant = project_obj.grant_set.order_by("-modified")[0]
            grant_updated_in_last_year = (now - latest_grant.created).days < 365
        else:
            grant_updated_in_last_year = None

        if project_obj.publication_set.exists():
            latest_publication = project_obj.publication_set.order_by("-created")[0]
            publication_updated_in_last_year = (now - latest_publication.created).days < 365
        else:
            publication_updated_in_last_year = None

        if grant_updated_in_last_year or publication_updated_in_last_year:
            self.fields["reason"].widget = forms.HiddenInput()
        else:
            self.fields["reason"].required = True


class ProjectReviewEmailForm(forms.Form):
    cc = forms.CharField(required=False)
    email_body = forms.CharField(required=True, widget=forms.Textarea)

    def __init__(self, pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_review_obj = get_object_or_404(ProjectReview, pk=int(pk))
        self.fields["email_body"].initial = "Dear {} {} \n{}".format(
            project_review_obj.project.pi.first_name,
            project_review_obj.project.pi.last_name,
            EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL,
        )
        self.fields["cc"].initial = ", ".join([EMAIL_DIRECTOR_EMAIL_ADDRESS] + EMAIL_ADMIN_LIST)


class ProjectAttributeAddForm(forms.ModelForm):
    class Meta:
        fields = "__all__"
        model = ProjectAttribute
        labels = {
            "proj_attr_type": "Project Attribute Type",
        }

    def __init__(self, *args, **kwargs):
        super(ProjectAttributeAddForm, self).__init__(*args, **kwargs)
        user = (kwargs.get("initial")).get("user")
        self.fields["proj_attr_type"].queryset = self.fields["proj_attr_type"].queryset.order_by(Lower("name"))
        if not user.is_superuser:
            self.fields["proj_attr_type"].queryset = self.fields["proj_attr_type"].queryset.filter(is_private=False)


class ProjectAttributeDeleteForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    name = forms.CharField(max_length=150, required=False, disabled=True)
    attr_type = forms.CharField(max_length=150, required=False, disabled=True)
    value = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pk"].widget = forms.HiddenInput()


# class ProjectAttributeChangeForm(forms.Form):
#     pk = forms.IntegerField(required=False, disabled=True)
#     name = forms.CharField(max_length=150, required=False, disabled=True)
#     value = forms.CharField(max_length=150, required=False, disabled=True)
#     new_value = forms.CharField(max_length=150, required=False, disabled=False)

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['pk'].widget = forms.HiddenInput()

#     def clean(self):
#         cleaned_data = super().clean()

#         if cleaned_data.get('new_value') != "":
#             proj_attr = ProjectAttribute.objects.get(pk=cleaned_data.get('pk'))
#             proj_attr.value = cleaned_data.get('new_value')
#             proj_attr.clean()


class ProjectAttributeUpdateForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    new_value = forms.CharField(max_length=150, required=True, disabled=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pk"].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("new_value") != "":
            proj_attr = ProjectAttribute.objects.get(pk=cleaned_data.get("pk"))
            proj_attr.value = cleaned_data.get("new_value")
            proj_attr.clean()


class ProjectCreationForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["title", "description", "field_of_science"]
