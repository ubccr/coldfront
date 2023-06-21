import csv
import logging
import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import  TemplateView, View
from django.db.models import Q
from django.db.models.query import QuerySet
from django.http.response import StreamingHttpResponse
from django.forms import formset_factory

from coldfront.plugins.advanced_exporting.forms import SearchForm, AllocationSearchForm, AllocationAttributeFormSetHelper
from coldfront.core.project.models import Project
from coldfront.core.allocation.models import Allocation, AllocationAttribute
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import Echo
from coldfront.plugins.advanced_exporting.util import TableBuilder

logger = logging.getLogger(__name__)


class ExportTableBuilder:
    def __init__(self, get_request, form_class):
        self.request = get_request

    def build_allocation_queryset(self, data):
        order_by = self.request.GET.get('order_by')
        # print(order_by)
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            if 'project' in order_by:
                # split = order_by.split('__')
                # order_by = '__'.join(split)
                order_by = direction + order_by
            elif 'resources' in order_by:
                split = order_by.split('__')
                order_by = '__'.join(split)
                order_by = direction + order_by
            else:
                order_by = direction + order_by.split('__')[1]
        else:
            order_by = 'project__id'
        # print(order_by)
        allocations = Allocation.objects.prefetch_related('project', 'status',).all().order_by(order_by)

        if data.get('allocation__status__name'):
            allocations = allocations.filter(
                status__in=data.get('allocation__status__name')
            )

        return allocations

    def build_project_queryset(self, data):
        order_by = 'id'
        if data.get('only_search_projects'):
            order_by = self.request.GET.get('order_by')
            if order_by:
                direction = self.request.GET.get('direction')
                if direction == 'asc':
                    direction = ''
                else:
                    direction = '-'

                split = order_by.split('__')[1:]
                order_by = '__'.join(split)
                order_by = direction + order_by
            else:
                order_by = 'id'

        projects = Project.objects.prefetch_related(
            'pi',
            'status',
            'type'
        ).all().order_by(order_by)

        if data.get('project__title'):
            projects = projects.filter(title__icontains= data.get('project__title'))
        if data.get('project__description'):
            projects = projects.filter(description__icontains= data.get('project__description'))
        if data.get('project__pi__username'):
            projects = projects.filter(pi__username__icontains= data.get('project__pi__username'))
        if data.get('project__requestor__username'):
            projects = projects.filter(
                requestor__username__icontains= data.get('project__requestor__username')
            )
        if data.get('project__status__name'):
            projects = projects.filter(status__in= data.get('project__status__name'))
        if data.get('project__type__name'):
            projects = projects.filter(type__in= data.get('project__type__name'))
        if data.get('project__class_number'):
            projects = projects.filter(class_number__icontains= data.get('project__class_number'))

        return projects

    def build_resource_queryset(self, data):
        resources = Resource.objects.prefetch_related('resource_type',).filter(is_allocatable=True)

        if data.get('resources__name'):
            resources = resources.filter(
                id__in=data.get('resources__name').values_list('id')
            )
        if data.get('resources__resource_type__name'):
            resources = resources.filter(
                resource__resource_type__in=data.get('resources__resource_type__name')
            )

        return resources

    # def add_allocation_attribute_parameters(self, data, allocation_queryset):
    #     if data.get('allocationattribute_name_1') and data.get('allocationattribute_value_1'):
    #         allocation_queryset = allocation_queryset.filter(
    #             Q(allocationattribute__allocation_attribute_type=data.get('allocationattribute_name_1')) &
    #             Q(allocationattribute__value__contains=data.get(
    #                 'allocationattribute_value_1'))
    #         )
        
    #     return allocation_queryset

    def build_queryset(self, data):
        allocation_queryset = self.build_allocation_queryset(data)

        project_queryset = self.build_project_queryset(data)
        allocation_queryset = allocation_queryset.filter(project__in=list(project_queryset))

        resource_queryset = self.build_resource_queryset(data)
        allocation_queryset = allocation_queryset.filter(resources__in=list(resource_queryset))

        # allocation_queryset = self.add_allocation_attribute_parameters(data, allocation_queryset)
        
        return allocation_queryset
    
    def build_project_columns(self, data):
        columns = []
        for key, value in data.items():
            if 'display' in key and 'project' in key and value:
                display_name = ' '.join(key.split('_')[1:])
                field_name = key[len('display') + 2:]
                enable_sorting = 'true'
                if 'title' in field_name or 'description' in field_name:
                    enable_sorting = 'false'
                columns.append({
                    'enable_sorting': enable_sorting,
                    'display_name': display_name.title(),
                    'field_name': field_name
                })

        return columns

    def build_project_rows(self, queryset, columns, data):
        column_field_names = [column.get('field_name') for column in columns]
        rows_dict = {}
        for i, result in enumerate(queryset):
            rows_dict[i] = []

            for column in column_field_names:
                split = column.split('__')[1:]
                nested_attribute = ""
                if len(split) == 2:
                    attribute, nested_attribute = split
                else:
                    attribute = split[0]

                attribute = getattr(result, attribute)
                if nested_attribute:
                    attribute = getattr(attribute, nested_attribute)

                rows_dict[i].append(attribute)

        return rows_dict

    def build(self, parameters):
        data = []
        print(parameters)
        search_form = SearchForm(parameters)
        if search_form.is_valid():
            data = search_form.cleaned_data
        else:
            return [], []
        if data.get('only_search_projects'):
            queryset = self.build_project_queryset(data)
            columns = self.build_project_columns(data)
            rows = self.build_project_rows(queryset, columns, data)
            return rows, columns

        # allocation_attributes = self.get_allocation_attributes(data)
        queryset = self.build_queryset(data)
        columns = self.build_columns(data)
        additional_columns = self.build_additional_columns(data)
        additional_data = self.get_additional_data(data)
        rows = self.build_rows(queryset, additional_data, columns, additional_columns)

        return rows, columns + additional_columns

    def get_additional_data(self, data):
        all_allocation_attributes = {}
        for key, value in data.items():
            allocation_attribute = []
            if 'allocationattribute__name' in key and value:
                allocation_attributes = AllocationAttribute.objects.filter(allocation_attribute_type=value)
                if allocation_attributes:
                    entries = []
                    for allocation_attribute in allocation_attributes:
                        entries.append(allocation_attribute)
                    all_allocation_attributes[allocation_attribute.allocation.id] = entries

        # print(all_allocation_attributes)
        return all_allocation_attributes

    def build_additional_columns(self, data):
        columns = []
        for key, value in data.items():
            if 'allocationattribute__name' in key and value:
                display_name = value.name
                field_name = key
                enable_sorting = 'false'
                columns.append({
                    'enable_sorting': enable_sorting,
                    'display_name': display_name,
                    'field_name': field_name,
                    'id': value.id
                })
        # for key, value in data.items():
        #     if 'display' in key and value:
        #         display_name = ' '.join(key.split('__')[1:])
        #         field_name = key[len('display') + 2:]
        #         enable_sorting = 'true'
        #         if 'title' in field_name or 'description' in field_name:
        #             enable_sorting = 'false'
        #         columns.append({
        #             'enable_sorting': enable_sorting,
        #             'display_name': display_name.title(),
        #             'field_name': field_name
        #         })
        # print(columns)
        return columns

    def build_rows(self, queryset, additional_data, columns, additional_columns):

        column_field_names = [column.get('field_name') for column in columns]
        rows_dict = {}
        for i, result in enumerate(queryset):
            rows_dict[i] = []

            for column in column_field_names:

                split = column.split('__')
                nested_attribute = ""
                if len(split) == 3:
                    model, attribute, nested_attribute = split
                else:
                    model, attribute = split

                if 'project' == model:
                    project = getattr(result, model)
                    attribute = getattr(project, attribute)
                elif 'resources' == model:
                    resource = result.get_parent_resource
                    # if attribute == 'type':
                    #     attribute = 'resource_type'
                    attribute = getattr(resource, attribute)
                else:
                    attribute = getattr(result, attribute)

                if nested_attribute:
                    attribute = getattr(attribute, nested_attribute)
                if attribute is None:
                    attribute = ""
                rows_dict[i].append(attribute)

            for additional_column in additional_columns:
                allocation_id = result.id
                allocation_attributes = additional_data.get(allocation_id)
                if allocation_attributes is not None:
                    value = ""
                    for allocation_attribute in allocation_attributes:
                        if allocation_attribute.allocation_attribute_type.id == additional_column.get('id'):
                            value = allocation_attribute.value
                            break

                    rows_dict[i].append(value)
                else:
                    rows_dict[i].append("")
        return rows_dict

    def build_columns(self, data):
        columns = []
        for key, value in data.items():
            if 'display' in key and value:
                display_name = ' '.join(key.split('__')[1:])
                field_name = key[len('display') + 2:]
                enable_sorting = 'true'
                if 'title' in field_name or 'description' in field_name:
                    enable_sorting = 'false'
                columns.append({
                    'enable_sorting': enable_sorting,
                    'display_name': display_name.title(),
                    'field_name': field_name
                })

        return columns


class AdvancedExportingView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name='advanced_exporting/advanced_exporting.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        allocation_search_formset = formset_factory(AllocationSearchForm, extra=2)
        if not self.request.GET:
            formset = allocation_search_formset(prefix='allocationattribute')
        else:
            formset = allocation_search_formset(self.request.GET, prefix='allocationattribute')
        allocationattribute_data = []
        for form in formset:
            if form.is_valid():
                allocationattribute_data.append(form.cleaned_data)
        context['allocationattribute_form'] = formset
        helper = AllocationAttributeFormSetHelper()
        context['allocationattribute_helper'] = helper
        search_form = SearchForm(self.request.GET, prefix='full_search')

        if search_form.is_valid():
            context['export_form'] = search_form
            data = search_form.cleaned_data
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
        builder = TableBuilder()
        #builder2 = ExportTableBuilder(self.request, AdvancedExportForm)
        # print(self.request.GET)
        if search_form.is_valid():
            data = search_form.cleaned_data
            rows, columns = builder.build_table(data, allocationattribute_data, self.request.GET)
        else:
            rows, columns = [], []
        print('COLUMNS')
        print(columns)
        # print(rows, columns)
        # columns = builder.build_columns()
        # rows = builder.build_rows()S

        #rows, columns = builder2.build(self.request.GET)
        context['filter_parameters'] = filter_parameters
        context['columns'] = columns
        num_rows = 0
        if columns:
            num_rows = len(rows)
        context['entries'] = num_rows
        context['rows'] = rows
        return context


class AdvancedExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        
    def post(self, request):
        print('POST')
        print(request.POST)
        print(request.POST.get('data'))
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
