from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.geode_project.forms import GeodeProjectForm

GEODE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD = import_from_settings(
    'GEODE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD', 10)

class GeodeProjectView:
    form_class = GeodeProjectForm
    template_name = 'geode_project/geodeproject.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['GEODE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD'] = GEODE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD
        return context

    def form_valid(self, form):
        form_data = form.cleaned_data

        if form_data.get('storage_space') < GEODE_PROJECT_ALLOCATED_QUANTITY_THRESHOLD / 2:
            form.cleaned_data['data_generation'] = ''
            form.cleaned_data['data_protection'] = ''
            form.cleaned_data['data_computational_lifetime'] = ''
            form.cleaned_data['expected_project_lifetime'] = ''

        http_response = super().form_valid(form)
        return http_response
