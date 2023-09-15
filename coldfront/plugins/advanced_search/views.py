import csv
import logging
import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import  TemplateView, View
from django.http.response import StreamingHttpResponse
from django.forms import formset_factory

from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.plugins.advanced_search.forms import SearchForm, AllocationAttributeSearchForm, AllocationAttributeFormSetHelper
from coldfront.core.utils.common import Echo
from coldfront.plugins.advanced_search.util import build_table

logger = logging.getLogger(__name__)


class AdvancedSearchView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name='advanced_search/advanced_search.html'

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        
        if user.has_perms(['project.can_view_all_projects', 'allocation.can_view_all_allocations']):
            return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_form = SearchForm(self.request.GET, prefix='full_search')

        selected_resources = None
        if search_form.is_valid():
            context['export_form'] = search_form
            data = search_form.cleaned_data
            selected_resources = data.get('resources__name')
        else:
            context['export_form'] = SearchForm(prefix='full_search')

        allocation_search_formset = formset_factory(AllocationAttributeSearchForm, extra=1)
        if not self.request.GET:
            formset = allocation_search_formset(prefix='allocationattribute')
        else:
            formset = allocation_search_formset(
                self.request.GET,
                prefix='allocationattribute',
                form_kwargs={'resources': selected_resources}
            )

        allocation_attribute_types_with_usage = list(AllocationAttributeType.objects.filter(
            has_usage=True
        ).values_list('id', flat=True))
        allocationattribute_data = []
        for form in formset:
            if form.is_valid():
                data = form.cleaned_data
                name = data['allocationattribute__name']
                if not name or not name.id in allocation_attribute_types_with_usage: 
                    data['allocationattribute__has_usage'] = '0'

                allocationattribute_data.append(form.cleaned_data)
        context['allocationattribute_form'] = formset
        helper = AllocationAttributeFormSetHelper()
        context['allocationattribute_helper'] = helper

        linked_allocation_attribute_types = {}
        for allocation_attribute_type in AllocationAttributeType.objects.all():
            resources = allocation_attribute_type.linked_resources.all()
            if resources.exists():
                for resource in resources:
                    if not linked_allocation_attribute_types.get(resource.id):
                        linked_allocation_attribute_types[resource.id] = []

                    linked_allocation_attribute_types[resource.id].append(
                        f'<option value="{allocation_attribute_type.id}">{allocation_attribute_type}</option>'
                    )

        if search_form.is_valid():
            data = search_form.cleaned_data
            rows, columns = build_table(data, allocationattribute_data, self.request.GET)
        else:
            rows, columns = [], []
        context['columns'] = columns
        num_rows = 0
        if columns:
            num_rows = len(rows)
        context['entries'] = num_rows
        context['rows'] = rows
        context['allocation_attribute_type_ids'] = allocation_attribute_types_with_usage
        context['linked_allocation_attribute_types'] = linked_allocation_attribute_types
        return context


class AdvancedExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        
        if user.has_perms(['project.can_view_all_projects', 'allocation.can_view_all_allocations']):
            return True
        
    def post(self, request):
        data = json.loads(request.POST.get('data'))
        columns = data.get('columns')
        column_names = [column.get('display_name') for column in columns]
        rows = data.get('rows')
        rows = [value for value in rows.values()]

        rows.insert(0, column_names)
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        response = StreamingHttpResponse(
            (writer.writerow(row) for row in rows),
            content_type='text/csv'
        )
        file_name = 'data'
        response['Content-Disposition'] = f'attachment; filename="{file_name}.csv"'

        logger.info(f'Admin {request.user.username} exported the advanced search list')

        return response
