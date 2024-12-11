from coldfront.plugins.geode_project.forms import GeodeProjectForm


class GeodeProjectView:
    form_class = GeodeProjectForm
    template_name = 'geode_project/geodeproject.html'

    def form_valid(self, form):
        http_response = super().form_valid(form)
        self.allocation_obj.end_date = None
        self.allocation_obj.save()

        return http_response
