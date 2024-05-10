from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.db.models.functions import Lower
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from coldfront.core.utils.views import ColdfrontListView
from coldfront.core.resource.models import Resource, ResourceAttribute
from coldfront.core.resource.forms import ResourceAttributeCreateForm, ResourceSearchForm, ResourceAttributeDeleteForm


class ResourceDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Resource
    template_name = 'resource_detail.html'
    context_object_name = 'resource'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        return True

    def get_child_resources(self, resource_obj):
        child_resources = list(resource_obj.resource_set.all().order_by('name'))

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

        attributes = list(resource_obj.resourceattribute_set.all().order_by(
                                        'resource_attribute_type__name'))

        child_resources = self.get_child_resources(resource_obj)

        context['resource'] = resource_obj
        context['attributes'] = attributes
        context['child_resources'] = child_resources

        return context

class ResourceAttributeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ResourceAttribute
    form_class = ResourceAttributeCreateForm
    # fields = '__all__'
    template_name = 'resource_resourceattribute_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True
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

            messages.success(request,
                    f'Deleted {attributes_deleted_count} attributes from resource.')
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('resource-detail', kwargs={'pk': pk}))

class ResourceListView(ColdfrontListView):
    model = Resource
    template_name = 'resource_list.html'
    context_object_name = 'item_list'

    def return_order(self):
        order_by = self.request.GET.get('order_by', 'id')
        direction = self.request.GET.get('direction', 'asc')
        if order_by != 'name':
            if direction == 'asc':
                direction = ''
            if direction == 'des':
                direction = '-'
            order_by = direction + order_by
        return order_by

    def get_queryset(self):

        order_by = self.return_order()
        resource_search_form = ResourceSearchForm(self.request.GET)

        if order_by == 'name':
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                resources = Resource.objects.all().order_by(Lower('name'))
            elif direction == 'des':
                resources = (Resource.objects.all().order_by(Lower('name')).reverse())
            else:
                resources = Resource.objects.all().order_by(order_by)
        else:
            resources = Resource.objects.all().order_by(order_by)
        if resource_search_form.is_valid():
            data = resource_search_form.cleaned_data

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
        return resources.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
                            SearchFormClass=ResourceSearchForm, **kwargs)
        return context
