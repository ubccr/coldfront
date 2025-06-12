# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, ListView

from coldfront.core.project.models import Project
from coldfront.core.research_output.forms import ResearchOutputForm
from coldfront.core.research_output.models import ResearchOutput
from coldfront.core.utils.mixins.views import (
    ChangesOnlyOnActiveProjectMixin,
    ProjectInContextMixin,
    SnakeCaseTemplateNameMixin,
    UserActiveManagerOrHigherMixin,
)


class ResearchOutputCreateView(
    UserActiveManagerOrHigherMixin,
    ChangesOnlyOnActiveProjectMixin,
    SuccessMessageMixin,
    SnakeCaseTemplateNameMixin,
    ProjectInContextMixin,
    CreateView,
):
    # directly using the exclude option isn't possible with CreateView; use such a form instead
    form_class = ResearchOutputForm

    model = ResearchOutput
    template_name_suffix = "_create"

    success_message = "Research Output added successfully."

    def form_valid(self, form):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        obj = form.save(commit=False)
        obj.created_by = self.request.user
        obj.project = project_obj

        self.object = obj

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("project-detail", kwargs={"pk": self.kwargs.get("project_pk")})


class ResearchOutputDeleteResearchOutputsView(
    UserActiveManagerOrHigherMixin,
    ChangesOnlyOnActiveProjectMixin,
    SnakeCaseTemplateNameMixin,
    ProjectInContextMixin,
    ListView,
):
    model = ResearchOutput  # only included to utilize SnakeCaseTemplateNameMixin
    template_name_suffix = "_delete_research_outputs"

    def get_queryset(self):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        return ResearchOutput.objects.filter(project=project_obj).order_by("-created")

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get("project_pk"))

        def get_normalized_posted_pks():
            posted_pks = set(request.POST.keys())
            posted_pks.remove("csrfmiddlewaretoken")
            return {int(x) for x in posted_pks}

        project_research_outputs = self.get_queryset()

        project_research_output_pks = set(project_research_outputs.values_list("pk", flat=True))
        posted_research_output_pks = get_normalized_posted_pks()

        # make sure we're told to delete something, else error to same page
        if not posted_research_output_pks:
            messages.error(request, "Please select some research outputs to delete, or go back to project.")
            return HttpResponseRedirect(request.path_info)

        # make sure the user plays nice
        if not project_research_output_pks >= posted_research_output_pks:
            raise PermissionDenied("Attempting to delete others' research outputs")

        num_deletions, _ = project_research_outputs.filter(pk__in=posted_research_output_pks).delete()

        msg = "Deleted {} research output{} from project.".format(
            num_deletions,
            "" if num_deletions == 1 else "s",
        )
        messages.success(request, msg)

        return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": project_obj.pk}))
