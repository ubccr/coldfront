from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (
    Project,
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)
from coldfront.plugins.qumulo.forms import ProjectCreateForm

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.urls import reverse
from django.views.generic.edit import FormView


class PluginProjectCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ProjectCreateForm
    model = Project
    template_name = "project/project_create_form.html"
    project = None

    def test_func(self):
        # bmulligan (20240626):
        # This function will likely need work (or removal) with the
        # permissions-related enhancements in the backlog
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.userprofile.is_pi:
            return True

    def form_valid(self, form: ProjectCreateForm):
        user = self.user_handler(form.cleaned_data["pi"])
        self.project = Project.objects.create(
            field_of_science=FieldOfScience.objects.get(
                id=form.cleaned_data["field_of_science"]
            ),
            title=form.cleaned_data["title"],
            pi=user,
            description=form.cleaned_data["description"],
            status=ProjectStatusChoice.objects.get(name="New"),
            force_review=False,
            requires_review=False,
        )
        project_user = ProjectUser.objects.create(
            user=user,
            project=self.project,
            role=ProjectUserRoleChoice.objects.get(name="Manager"),
            status=ProjectUserStatusChoice.objects.get(name="Active"),
        )
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super(PluginProjectCreateView, self).get_form_kwargs()
        kwargs["user_id"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("project-detail", kwargs={"pk": self.project.pk})

    def user_handler(self, user: str):
        return User.objects.get_or_create(username=user)[0]
