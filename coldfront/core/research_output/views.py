import csv
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect,StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import CreateView, ListView
from django.forms import formset_factory

from coldfront.core.utils.common import Echo
from coldfront.core.project.models import Project
from coldfront.core.research_output.forms import ResearchOutputForm, ResearchOutputReportForm
from coldfront.core.research_output.models import ResearchOutput
from coldfront.core.utils.mixins.views import (
    UserActiveManagerOrHigherMixin,
    ChangesOnlyOnActiveProjectMixin,
    ProjectInContextMixin,
    SnakeCaseTemplateNameMixin,
)


class ResearchOutputReportView(ListView):
    template_name = 'research_output/research_output_report.html'

    _research_output_fields_for_end = ['created_by', 'project', 'created', 'modified']

    def get_r_outputs(self):
        research_outputs = ResearchOutput.objects.all()

        research_outputs=[
            {
                "pk":research_output.pk,
                "title":research_output.title,
                "description":research_output.description,
                "project":research_output.project.title,
                "created_by":research_output.created_by,
                "created":research_output.created
            }
            for research_output in research_outputs
        ]
        return research_outputs

    def get(self,request):
        
        context = {}
        research_outputs=self.get_r_outputs()
        formset = formset_factory(ResearchOutputReportForm,max_num=len(research_outputs))
        formset = formset(initial=research_outputs, prefix='researchoutputform')
        context["formset"] = formset



        return render(request, self.template_name, context)


    
    def post(self, request, *args, **kwargs):
        research_outputs = self.get_r_outputs()

        formset = formset_factory(ResearchOutputReportForm,max_num=len(research_outputs))
        formset = formset(request.POST, initial=research_outputs, prefix='researchoutputform')

        header = [
            "Title",
            "Description",
            "Created By",
            "Project",
            "Created"
        ]
        rows = []
        research_outputs_selected = 0

        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                if(form_data):
                    if form_data['selected']:
                        research_output_1 = get_object_or_404(ResearchOutput, pk=form_data['pk'])

                        row = [
                            research_output_1.title,
                            research_output_1.description,
                            research_output_1.created_by,
                            research_output_1.project,
                            research_output_1.created,
                        
                        ]
                        rows.append(row)
                        research_outputs_selected += 1

            if research_outputs_selected == 0:
                research_outputs_2 = ResearchOutput.objects.all()
                for research_output in research_outputs_2:
                    row = [
                        research_output.title,
                        research_output.description,
                        research_output.created_by,
                        research_output.project,
                        research_output.created,
                    ]
                    rows.append(row)

            rows.insert(0, header)
            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)
            response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                            content_type="text/csv")
            response['Content-Disposition'] = 'attachment; filename="researchoutput_report.csv"'
            return response
        else:
            for error in formset.errors:
                messages.error(request, error)
            return HttpResponseRedirect(reverse('research-output-report'))



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


class ResearchOutputDeleteResearchOutputsView(
        UserActiveManagerOrHigherMixin,
        ChangesOnlyOnActiveProjectMixin,
        SnakeCaseTemplateNameMixin,
        ProjectInContextMixin,
        ListView):

    model = ResearchOutput  # only included to utilize SnakeCaseTemplateNameMixin
    template_name_suffix = '_delete_research_outputs'

    def get_queryset(self):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        return ResearchOutput.objects.filter(project=project_obj).order_by('-created')

    def post(self, request, *args, **kwargs):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        def get_normalized_posted_pks():
            posted_pks = set(request.POST.keys())
            posted_pks.remove('csrfmiddlewaretoken')
            return {int(x) for x in posted_pks}

        project_research_outputs = self.get_queryset()

        project_research_output_pks = set(project_research_outputs.values_list('pk', flat=True))
        posted_research_output_pks = get_normalized_posted_pks()

        # make sure we're told to delete something, else error to same page
        if not posted_research_output_pks:
            messages.error(request, 'Please select some research outputs to delete, or go back to project.')
            return HttpResponseRedirect(request.path_info)

        # make sure the user plays nice
        if not project_research_output_pks >= posted_research_output_pks:
            raise PermissionDenied("Attempting to delete others' research outputs")

        num_deletions, _ = project_research_outputs.filter(pk__in=posted_research_output_pks).delete()

        msg = 'Deleted {} research output{} from project.'.format(
            num_deletions,
            '' if num_deletions == 1 else 's',
        )
        messages.success(request, msg)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
