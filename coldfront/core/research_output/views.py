from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView

from coldfront.core.project.models import Project
from coldfront.core.research_output.forms import ResearchOutputForm
from coldfront.core.research_output.models import ResearchOutput
from coldfront.core.utils.mixins.views import (
    UserActiveManagerOrHigherMixin,
    ChangesOnlyOnActiveProjectMixin,
    ProjectInContextMixin,
    SnakeCaseTemplateNameMixin,
)


class ResearchOutputCreateView(
        UserActiveManagerOrHigherMixin,
        ChangesOnlyOnActiveProjectMixin,
        SuccessMessageMixin,
        SnakeCaseTemplateNameMixin,
        ProjectInContextMixin,
        CreateView):

    # directly using the exclude option isn't possible with CreateView; use such a form instead
    form_class = ResearchOutputForm

    model = ResearchOutput
    template_name_suffix = '_create'

    success_message = 'Research Output added successfully.'

    def form_valid(self, form):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        obj = form.save(commit=False)
        obj.created_by = self.request.user
        obj.project = project_obj

        self.object = obj

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.kwargs.get('project_pk')})
