from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.forms import formset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template
import datetime

from coldfront.core.resource.forms import ResourceSearchForm, ResourceAttributeDeleteForm
from coldfront.core.resource.models import Resource, ResourceAttribute
from coldfront.core.allocation.models import Allocation

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
EMAIL_RESOURCE_EXPIRING_NOTIFICATION_DAYS = import_from_settings(
    'EMAIL_RESOURCE_EXPIRING_NOTIFICATION_DAYS', [7, ])
if EMAIL_ENABLED:
    CENTER_NAME = import_from_settings('CENTER_NAME')
    CENTER_BASE_URL = import_from_settings('CENTER_BASE_URL')
    EMAIL_RESOURCE_NOTIFICATIONS_ENABLED = import_from_settings('EMAIL_RESOURCE_NOTIFICATIONS_ENABLED', False)
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')

class ResourceDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Resource
    template_name = 'resource_detail.html'
    context_object_name = 'resource'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        return True

    def get_child_resources(self, resource_obj):
        child_resources = [resource for resource in resource_obj.resource_set.all(
        ).order_by('name')]

        child_resources = [

            {'object': resource,
             'WarrantyExpirationDate': resource.get_attribute('WarrantyExpirationDate'),
             'ServiceEnd': resource.get_attribute('ServiceEnd'),
             'Vendor': resource.get_attribute('Vendor'),
             'SerialNumber': resource.get_attribute('SerialNumber'),
             'Model': resource.get_attribute('Model'),            
             }

            for resource in child_resources
        ]

        return child_resources

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        resource_obj = get_object_or_404(Resource, pk=pk)

        attributes = [attribute for attribute in resource_obj.resourceattribute_set.all(
        ).order_by('resource_attribute_type__name')]

        child_resources = self.get_child_resources(resource_obj)

        context['resource'] = resource_obj
        context['attributes'] = attributes
        context['child_resources'] = child_resources

        attributes_warranty = resource_obj.get_attribute('WarrantyExpirationDate')
        attributes_service = resource_obj.get_attribute('ServiceEnd')

        attribute_warranty_day = -1 
        attribute_service_day = -1
        child_day = {}

        for days_remaining in sorted(set(EMAIL_RESOURCE_EXPIRING_NOTIFICATION_DAYS), reverse=True):

            expring_in_days = datetime.datetime.today().date()

            if attributes_warranty != None:
                warranty_day = (datetime.datetime.strptime(attributes_warranty, '%m/%d/%Y').date() - expring_in_days).days
                if warranty_day >= 0 and warranty_day <= days_remaining:
                    attribute_warranty_day = days_remaining

            if attributes_service != None:
                service_day = (datetime.datetime.strptime(attributes_service, '%m/%d/%Y').date() - expring_in_days).days
                if service_day >= 0 and service_day <= days_remaining:
                    attribute_service_day = days_remaining

            for resource in child_resources:
                if resource['object'] not in child_day:
                    child_day[resource['object']] = [-1,-1]

                if resource['WarrantyExpirationDate'] != None:
                    warranty_day = (datetime.datetime.strptime(resource['WarrantyExpirationDate'], '%m/%d/%Y').date() - expring_in_days).days

                    if warranty_day >= 0 and warranty_day <= days_remaining:
                        child_day[resource['object']][0] = days_remaining

                if resource['ServiceEnd'] != None:
                    service_day = (datetime.datetime.strptime(resource['ServiceEnd'], '%m/%d/%Y').date() - expring_in_days).days

                    if service_day >= 0 and service_day <= days_remaining:
                        child_day[resource['object']][1] = days_remaining

        if (attribute_warranty_day != -1 and attribute_service_day != -1):
                messages.warning(self.request, f'{resource_obj.name} warranty is expiring within {attribute_warranty_day} day(s)' +
                                                f' and service expiring within {attribute_service_day} day(s)')
        else:
            if (attribute_warranty_day != -1):
                messages.warning(self.request, f'{resource_obj.name} warranty is expiring within {attribute_warranty_day} day(s)')

            if (attribute_service_day != -1):
                messages.warning(self.request, f'{resource_obj.name} service is expiring within {attribute_service_day} day(s)')  

        for resource_key, resource_value in child_day.items():
            if (resource_value[0] != -1 and resource_value[1] != -1):
                messages.warning(self.request, f'{resource_key} warranty is expiring within {resource_value[0]} day(s)' +
                                                f' and service expiring within {resource_value[1]} day(s)')
            else:
                if (resource_value[0] != -1):
                    messages.warning(self.request, f'{resource_key} warranty is expiring within {resource_value[0]} day(s)')

                if (resource_value[1] != -1):
                    messages.warning(self.request, f'{resource_key} service is expiring within {resource_value[1]} day(s)')

        return context

class ResourceAttributeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ResourceAttribute
    fields = '__all__'
    template_name = 'resource_resourceattribute_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True
        else:
            messages.error(
                self.request, 'You do not have permission to add resource attributes.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        resource_obj = get_object_or_404(Resource, pk=pk)
        context['resource'] = resource_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get('pk')
        resource_obj = get_object_or_404(Resource, pk=pk)
        initial['resource'] = resource_obj
        return initial

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        form = super().get_form(form_class)
        form.fields['resource'].widget = forms.HiddenInput()
        return form

    def get_success_url(self):
        return reverse('resource-detail', kwargs={'pk': self.kwargs.get('pk')})


class ResourceAttributeDeleteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'resource_resourceattribute_delete.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        else:
            messages.error(
                self.request, 'You do not have permission to delete resource attributes.')

    def get_resource_attributes_to_delete(self, resource_obj):

        resource_attributes_to_delete = ResourceAttribute.objects.filter(
            resource=resource_obj)
        resource_attributes_to_delete = [

            {'pk': attribute.pk,
             'name': attribute.resource_attribute_type.name,
             'value': attribute.value,
             }

            for attribute in resource_attributes_to_delete
        ]

        return resource_attributes_to_delete

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        resource_obj = get_object_or_404(Resource, pk=pk)

        resource_attributes_to_delete = self.get_resource_attributes_to_delete(
            resource_obj)
        context = {}

        if resource_attributes_to_delete:
            formset = formset_factory(ResourceAttributeDeleteForm, max_num=len(
                resource_attributes_to_delete))
            formset = formset(
                initial=resource_attributes_to_delete, prefix='attributeform')
            context['formset'] = formset
        context['resource'] = resource_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        resource_obj = get_object_or_404(Resource, pk=pk)

        resource_attributes_to_delete = self.get_resource_attributes_to_delete(
            resource_obj)

        formset = formset_factory(ResourceAttributeDeleteForm, max_num=len(
            resource_attributes_to_delete))
        formset = formset(
            request.POST, initial=resource_attributes_to_delete, prefix='attributeform')

        attributes_deleted_count = 0

        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                if form_data['selected']:

                    attributes_deleted_count += 1

                    resource_attribute = ResourceAttribute.objects.get(
                        pk=form_data['pk'])
                    resource_attribute.delete()

            messages.success(request, 'Deleted {} attributes from resource.'.format(
                attributes_deleted_count))
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('resource-detail', kwargs={'pk': pk}))

class ResourceListView(LoginRequiredMixin, ListView):

    model = Resource
    template_name = 'resource_list.html'
    context_object_name = 'resource_list'
    paginate_by = 25

    def get_queryset(self):

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = 'id'

        resource_search_form = ResourceSearchForm(self.request.GET)

        if resource_search_form.is_valid():
            data = resource_search_form.cleaned_data
            resources = Resource.objects.all().order_by(order_by)

            if data.get('show_allocatable_resources'):
                resources = resources.filter(is_allocatable=True)
            if data.get('model'):
                resources = resources.filter(
                    Q(resourceattribute__resource_attribute_type__name='Model') &
                    Q(resourceattribute__value=data.get('model'))
                )
            if data.get('serialNumber'):
                resources = resources.filter(
                    Q(resourceattribute__resource_attribute_type__name='SerialNumber') &
                    Q(resourceattribute__value=data.get('serialNumber'))
                )
            if data.get('installDate'):
                resources = resources.filter(
                    Q(resourceattribute__resource_attribute_type__name='InstallDate') &
                    Q(resourceattribute__value=data.get('installDate').strftime('%m/%d/%Y'))
                )
            if data.get('serviceStart'):
                resources = resources.filter(
                    Q(resourceattribute__resource_attribute_type_name='ServiceStart') &
                    Q(resourceattribute__value=data.get('serviceStart').strftime('%m/%d/%Y'))
                )
            if data.get('serviceEnd'):
                resources = resources.filter(
                    Q(resourceattribute__resource_attribute_type__name='ServiceEnd') &
                    Q(resourceattribute__value=data.get('serviceEnd').strftime('%m/%d/%Y'))
                )
            if data.get('warrantyExpirationDate'):
                resources = resources.filter(
                    Q(resourceattribute__resource_attribute_type__name='WarrantyExpirationDate') &
                    Q(resourceattribute__value=data.get('warrantyExpirationDate').strftime('%m/%d/%Y'))
                )
            if data.get('vendor'):
                resources = resources.filter(
                    Q(resourceattribute__resource_attribute_type__name='Vendor') &
                    Q(resourceattribute__value=data.get('vendor'))
                )
        else:
            resources = Resource.objects.all().order_by(order_by)
        return resources.distinct()

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        resources_count = self.get_queryset().count()
        context['resources_count'] = resources_count

        resource_search_form = ResourceSearchForm(self.request.GET)
        if resource_search_form.is_valid():
            context['resource_search_form'] = resource_search_form
            data = resource_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['resource_search_form'] = resource_search_form
        else:
            filter_parameters = None
            context['resource_search_form'] = ResourceSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                'order_by=%s&direction=%s&' % (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        if filter_parameters:
            context['expand_accordion'] = 'show'

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        resource_list = context.get('resource_list')
        paginator = Paginator(resource_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            resource_list = paginator.page(page)
        except PageNotAnInteger:
            resource_list = paginator.page(1)
        except EmptyPage:
            resource_list = paginator.page(paginator.num_pages)
        return context

