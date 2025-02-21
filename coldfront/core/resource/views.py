import logging

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import (
    Q, F, Value, Count, Case, When, 
    Subquery, OuterRef, CharField, IntegerField, FloatField
)
from django.db.models.functions import (
    Substr, StrIndex, Concat, Coalesce,
    Cast, Length
)
from django.db.models.functions import Lower
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from coldfront.core.utils.views import ColdfrontListView
from coldfront.core.resource.models import Resource, ResourceAttribute
from coldfront.core.resource.forms import (
    ResourceAttributeCreateForm,
    ResourceSearchForm,
    ResourceAttributeDeleteForm,
    ResourceAllocationUpdateForm,
)
from coldfront.core.allocation.models import AllocationStatusChoice, AllocationAttributeType, AllocationAttribute, Allocation
from coldfront.core.allocation.signals import allocation_raw_share_edit

from coldfront.plugins.slurm.utils import SlurmError

from coldfront.core.project.models import ProjectUser

logger = logging.getLogger(__name__)

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
        inactive_status = AllocationStatusChoice.objects.get(name='Inactive')
        allocations = resource_obj.allocation_set.exclude(
            status=inactive_status
        ).prefetch_related('project', 'allocationattribute_set')
        if 'Cluster' in resource_obj.resource_type.name:
            total_hours = sum([a.usage for a in allocations if a.usage])
            context['total_hours'] = total_hours

            # Get attribute type IDs
            slurm_specs_type = AllocationAttributeType.objects.get(name='slurm_specs')
            usage_type = AllocationAttributeType.objects.get(name='Core Usage (Hours)')
            effectv_type = AllocationAttributeType.objects.get(name='EffectvUsage')

            allocations = (
                allocations.annotate(
                    project_title=F('project__title'),
                    user_count=Cast(Count(
                        'allocationuser__id',
                        filter=Q(allocationuser__status__name='Active'),
                        distinct=True
                    ), IntegerField()),
                    # For slurm_specs parsing
                    specs_value=Subquery(
                        AllocationAttribute.objects
                        .filter(
                            allocation_id=OuterRef('id'),
                            allocation_attribute_type=slurm_specs_type
                        )
                        .values('value')[:1]
                    ),
                    rawshares=Substr(
                        'specs_value',
                        StrIndex('specs_value', Value('RawShares=')) + 10,
                        Cast(StrIndex(
                            Substr(
                                'specs_value',
                                StrIndex('specs_value', Value('RawShares=')) + 10
                            ),
                            Value(',')
                        ) - 1, IntegerField())
                    ),
                    normshares=Substr(
                        'specs_value',
                        StrIndex('specs_value', Value('NormShares=')) + 11,
                        Cast(StrIndex(
                            Substr(
                                'specs_value',
                                StrIndex('specs_value', Value('NormShares=')) + 11
                            ),
                            Value(',')
                        ) - 1, IntegerField())
                    ),
                    fairshare=Substr(
                        'specs_value',
                        StrIndex('specs_value', Value('FairShare=')) + 10,
                        Length('specs_value')
                    ),
                    usage=Cast(Coalesce(
                        Subquery(
                            AllocationAttribute.objects
                            .filter(
                                allocation_id=OuterRef('id'),
                                allocation_attribute_type=usage_type
                            )
                            .values('value')[:1]
                        ),
                        Value('0')
                    ), FloatField()),
                    effectvusage=Cast(Coalesce(
                        Subquery(
                            AllocationAttribute.objects
                            .filter(
                                allocation_id=OuterRef('id'),
                                allocation_attribute_type=effectv_type
                            )
                            .values('value')[:1]
                        ),
                        Value('0')
                    ), FloatField())
                )
                .order_by('id')
                .values(
                    'id',
                    'project_title',
                    'user_count',
                    'rawshares',
                    'normshares',
                    'fairshare',
                    'usage',
                    'effectvusage'
                )
            )

        context['allocations'] = allocations
        context['resource'] = resource_obj
        context['attributes'] = attributes
        context['child_resources'] = child_resources
        context['user_is_manager'] = resource_obj.user_can_manage_resource(self.request.user)
        context['resource_admin_list'] = resource_obj.allowed_users.values('username', 'full_name', 'email')
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

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        resource_obj = get_object_or_404(Resource, pk=pk)

        resource_attributes_to_delete = list(resource_obj.resourceattribute_set.values(
            'pk', 'value', name=F('resource_attribute_type__name')
        ))
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

        resource_attributes_to_delete = list(resource_obj.resourceattribute_set.values(
            'pk', 'value', name=F('resource_attribute_type__name')
        ))

        formset = formset_factory(ResourceAttributeDeleteForm, max_num=len(
            resource_attributes_to_delete))
        formset = formset(
            request.POST,
            initial=resource_attributes_to_delete,
            prefix='attributeform'
        )

        attrs_deleted_count = 0
        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                if form_data['selected']:
                    attrs_deleted_count += 1

                    resource_attribute = ResourceAttribute.objects.get(
                        pk=form_data['pk'])
                    resource_attribute.delete()

            messages.success(
                request, f'Deleted {attrs_deleted_count} attributes from resource.'
            )
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
            if data.get('resource_name'):
                resources = resources.filter(
                    name__icontains=data.get('resource_name')
                )
            if data.get('resource_type'):
                resources = resources.filter(
                    resource_type=data.get('resource_type')
                )

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


class ResourceAllocationsEditView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'resource_allocations_edit.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        resource_obj = get_object_or_404(Resource, pk=self.kwargs.get('pk'))
        if resource_obj.user_can_manage_resource(self.request.user):
            return True
        err = 'You do not have permission to edit resource allocations.'
        messages.error(self.request, err)
        return False

    def dispatch(self, request, *args, **kwargs):
        resource_obj = get_object_or_404(Resource, pk=self.kwargs.get('pk'))
        err = None
        if 'Storage' in resource_obj.resource_type.name:
            err = 'You cannot bulk-edit storage allocations.'
        if err:
            messages.error(request, err)
            return HttpResponseRedirect(
                reverse('resource-detail', kwargs={'pk': resource_obj.pk})
            )
        return super().dispatch(request, *args, **kwargs)

    def get_formset_initial_data(self, resource_allocations):
        edit_allocations_formset_initial_data = []
        if resource_allocations:
            for allocation in resource_allocations:
                slurm_specs_attribute = allocation.get_full_attribute('slurm_specs')
                if slurm_specs_attribute is not None:
                    edit_allocations_formset_initial_data.append(
                        {
                            'allocation_pk': allocation.pk,
                            'rawshare': allocation.get_slurm_spec_value('RawShares'),
                            'project': allocation.project.title,
                            'usage': allocation.usage,
                            'user_count': allocation.allocationuser_set.count(),
                        }
                    )
        return edit_allocations_formset_initial_data

    def get_context_data(self, resource_obj):
        context = {}
        resource_allocations = resource_obj.allocation_set.filter(
            status__name='Active'
        ).select_related('project').prefetch_related('allocationattribute_set')
        if resource_allocations:
            ResourceAllocationUpdateFormSet = formset_factory(
                ResourceAllocationUpdateForm,
                max_num=len(resource_allocations),
                extra=0
            )
            edit_allocations_formset_initial_data = self.get_formset_initial_data(resource_allocations)
            formset = ResourceAllocationUpdateFormSet(
                initial=edit_allocations_formset_initial_data,
                prefix='allocationsform'
            )
            context['formset'] = formset
        context['resource'] = resource_obj
        return context

    def get(self, request, *args, **kwargs):
        resource_obj = get_object_or_404(Resource, pk=self.kwargs.get('pk'))
        context = self.get_context_data(resource_obj)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        resource_obj = get_object_or_404(Resource, pk=pk)
        resource_allocations = resource_obj.allocation_set.filter(
            status__name='Active'
        ).select_related('project').prefetch_related('allocationattribute_set')
        ResourceAllocationUpdateFormSet = formset_factory(
            ResourceAllocationUpdateForm, max_num=len(resource_allocations), extra=0
        )
        edit_allocations_formset_initial_data = self.get_formset_initial_data(resource_allocations)
        formset = ResourceAllocationUpdateFormSet(
            request.POST, initial=edit_allocations_formset_initial_data, prefix='allocationsform'
        )
        if formset.is_valid():
            allocation_rawshares = {
                str(form.cleaned_data.get('allocation_pk')): form.cleaned_data.get('rawshare')
                for form in formset.forms
            }
            for allocation in resource_allocations:
                current_rawshare = allocation.get_slurm_spec_value('RawShares')
                new_rawshare = allocation_rawshares.get(str(allocation.pk), None)
                if new_rawshare and current_rawshare != new_rawshare: # Ignore unchanged values
                    logger.info(f'recognized changes in RawShares value for {allocation.project.title} slurm account: {current_rawshare} changed to {new_rawshare}')
                    try:
                        allocation_raw_share_edit.send(
                            sender=self.__class__,
                            account=allocation.project.title,
                            raw_share=new_rawshare
                        )
                        msg = f'RawShares value for {allocation.project.title} slurm account successfully updated from {current_rawshare} to {new_rawshare}'
                        logger.info(msg)
                        messages.success(request, msg)
                    except SlurmError as e:
                        err = f'Problem encountered while editing RawShares value for {allocation.project.title} slurm account: {e}'
                        logger.exception(err)
                        messages.error(request, err)
                    spec_update = allocation.update_slurm_spec_value('RawShares', new_rawshare)
                    if spec_update != True:
                        err = f'Slurm account for {allocation.project.title} successfully updated, but a problem was encountered while reflecting the updates in ColdFront: {spec_update}'
                        logger.error(err)
                        messages.error(request, err)

            messages.success(request, 'Allocation update complete.')
            return HttpResponseRedirect(reverse('resource-detail', kwargs={'pk': pk}))
        else:
            messages.error(request, 'Errors encountered, changes not saved. Check the form for details')
            context = self.get_context_data(resource_obj)
            context['formset'] = formset
            return render(request, self.template_name, context)
