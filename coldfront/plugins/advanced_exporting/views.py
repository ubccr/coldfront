import csv
import logging
import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import  TemplateView, View
from django.db.models.query import QuerySet
from django.http.response import StreamingHttpResponse
from django.forms import formset_factory

from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.plugins.advanced_exporting.forms import SearchForm, AllocationSearchForm, AllocationAttributeFormSetHelper
from coldfront.core.utils.common import Echo
from coldfront.plugins.advanced_exporting.util import build_table

logger = logging.getLogger(__name__)


class AdvancedExportingView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name='advanced_exporting/advanced_exporting.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_form = SearchForm(self.request.GET, prefix='full_search')

        selected_resources = None
        if search_form.is_valid():
            context['export_form'] = search_form
            data = search_form.cleaned_data
            selected_resources = data.get('resources__name')
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, QuerySet):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele.pk)
                    elif hasattr(value, 'pk'):
                        filter_parameters += '{}={}&'.format(key, value.pk)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['export_form'] = search_form
        else:
            filter_parameters = ''
            context['export_form'] = SearchForm(prefix='full_search')

        allocation_search_formset = formset_factory(AllocationSearchForm, extra=1)
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

        # print(filter_parameters)

        order_by = self.request.GET.get('order_by')
        # if order_by:
        #     direction = self.request.GET.get('direction')
        #     filter_parameters_with_order_by = filter_parameters + \
        #         'order_by=%s&direction=%s&' % (order_by, direction)
        # else:
        #     filter_parameters_with_order_by = filter_parameters

        # context['filter_parameters_with_order_by'] = filter_parameters_with_order_by
        # print(self.request.GET)
        if search_form.is_valid():
            data = search_form.cleaned_data
            rows, columns = build_table(data, allocationattribute_data, self.request.GET)
        else:
            rows, columns = [], []
        context['filter_parameters'] = filter_parameters
        context['columns'] = columns
        num_rows = 0
        if columns:
            num_rows = len(rows)
        context['entries'] = num_rows
        context['rows'] = rows
        context['allocation_attribute_type_ids'] = allocation_attribute_types_with_usage
        return context


class AdvancedExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        
    def post(self, request):
        # print('POST')
        # print(request.POST)
        # print(request.POST.get('data'))
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

        logger.info(f'Admin {request.user.username} exported the project user list')

        return response
