# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import re

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse

from coldfront.core.project.models import Project


class SnakeCaseTemplateNameMixin:
    # by default:
    # Django converts the model class name to simply lowercase (i.e. not snake_case)
    # however, we use snake_case filename style throughout coldfront
    #
    # thus, for consistency:
    # override get_template_names() to use snake_case instead of simply lowercase

    def get_template_names(self):
        def to_snake(string):
            # note that this is an oversimplified implementation
            # it should work in the majority of cases, even allowing us to change app/class/etc. names
            # but cases like DOIDisplay (or similar, using multiple caps in a row) would fail

            return string[0].lower() + re.sub("([A-Z])", r"_\1", string[1:]).lower()

        app_label = self.model._meta.app_label
        model_name = self.model.__name__

        return ["{}/{}{}.html".format(app_label, to_snake(model_name), self.template_name_suffix)]


class ProjectInContextMixin:
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["project"] = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        return context


class ChangesOnlyOnActiveProjectMixin:
    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))
        if project_obj.status.name not in [
            "Active",
            "New",
        ]:
            messages.error(request, "You cannot modify an archived project.")
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)


class UserActiveManagerOrHigherMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(
            user=self.request.user, role__name="Manager", status__name="Active"
        ).exists():
            return True
