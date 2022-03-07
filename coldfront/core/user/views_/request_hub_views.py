from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.views.generic.base import TemplateView

from coldfront.core.allocation.models import (AllocationAttributeType,
                                              AllocationUserAttribute,
                                              AllocationRenewalRequest,
                                              AllocationAdditionRequest)
from coldfront.core.project.models import (ProjectUserRemovalRequest,
                                           SavioProjectAllocationRequest,
                                           VectorProjectAllocationRequest,
                                           ProjectUserJoinRequest, Project)
from coldfront.core.project.utils_.permissions_utils import \
    is_user_manager_or_pi_of_project


class RequestListItem:
    """
    Object to keep track of all variables used in for each request type
    in the request hub
    """

    __slots__ = ['num', 'title', 'num_pending', 'table',
                 'pending_queryset', 'complete_queryset',
                 'button_path', 'button_text', 'id',
                 'help_text']


class RequestHubView(LoginRequiredMixin,
                     UserPassesTestMixin,
                     TemplateView):
    template_name = 'request_hub/request_hub.html'
    paginate_by = 10
    paginators = 0
    show_all_requests = False

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.show_all_requests:
            if self.request.user.is_superuser or self.request.user.is_staff:
                return True
        else:
            return True

    def create_paginator(self, queryset):
        """
        Creates a paginator object for the given queryset
        and updates the context with the created object.
        """
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get(f'page{self.paginators}')
        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)
        except EmptyPage:
            queryset = paginator.page(paginator.num_pages)

        self.paginators += 1

        return queryset

    def get_cluster_account_request(self):
        """Populates a RequestListItem with data for cluster account requests"""
        cluster_request_object = RequestListItem()

        user = self.request.user

        cluster_account_status = AllocationAttributeType.objects.get(
            name='Cluster Account Status')
        kwargs = {'allocation_attribute_type': cluster_account_status}

        if not self.show_all_requests:
            kwargs['allocation_user__user'] = user

        cluster_account_list_complete = \
            AllocationUserAttribute.objects.filter(
                value__in=['Denied', 'Active'], **kwargs).order_by(
                'modified')

        cluster_account_list_pending = \
            AllocationUserAttribute.objects.filter(
                value__in=['Pending - Add', 'Processing'], **kwargs).order_by(
                'modified')

        cluster_request_object.num = self.paginators
        cluster_request_object.pending_queryset = \
            self.create_paginator(cluster_account_list_pending)

        cluster_request_object.complete_queryset = \
            self.create_paginator(cluster_account_list_complete)

        cluster_request_object.num_pending = cluster_account_list_pending.count()

        cluster_request_object.title = 'Cluster Access Requests'
        cluster_request_object.table = \
            'allocation/allocation_cluster_account_request_list_table.html'
        cluster_request_object.button_path = \
            'allocation-cluster-account-request-list'
        cluster_request_object.button_text = \
            'Go To Cluster Access Requests Main Page'
        cluster_request_object.id = 'cluster_access_request_section'
        cluster_request_object.help_text = \
            'Showing your cluster access requests.'

        return cluster_request_object

    def get_project_removal_request(self):
        """Populates a RequestListItem with data for project removal requests"""
        removal_request_object = RequestListItem()
        user = self.request.user

        args = []
        if not self.show_all_requests:
            args.append(Q(project_user__user=user) | Q(requester=user))

        removal_request_pending = \
            ProjectUserRemovalRequest.objects.filter(
                status__name__in=['Pending', 'Processing'], *args).order_by(
                'modified')

        removal_request_complete = \
            ProjectUserRemovalRequest.objects.filter(
                status__name='Complete', *args).order_by(
                'modified')

        removal_request_object.num = self.paginators
        removal_request_object.pending_queryset = \
            self.create_paginator(removal_request_pending)

        removal_request_object.complete_queryset = \
            self.create_paginator(removal_request_complete)

        removal_request_object.num_pending = removal_request_pending.count()

        removal_request_object.title = 'Project Removal Requests'
        removal_request_object.table = \
            'project/project_removal/project_removal_request_list_table.html'
        removal_request_object.button_path = \
            'project-removal-request-list'
        removal_request_object.button_text = \
            'Go To Project Removal Requests Main Page'
        removal_request_object.id = 'project_removal_request_section'
        removal_request_object.help_text = \
            'Showing project removal requests that you requested or requests ' \
            'in which you are the user being removed.'

        return removal_request_object

    def get_savio_project_request(self):
        """Populates a RequestListItem with data for savio project requests"""
        savio_proj_request_object = RequestListItem()
        user = self.request.user

        args = []
        if not self.show_all_requests:
            args.append(Q(pi=user) | Q(requester=user))

        project_request_pending = \
            SavioProjectAllocationRequest.objects.filter(
                status__name__in=['Under Review', 'Approved - Processing'],
                *args).order_by(
                'modified')

        project_request_complete = \
            SavioProjectAllocationRequest.objects.filter(
                status__name__in=['Approved - Complete', 'Denied'],
                *args).order_by(
                'modified')

        savio_proj_request_object.num = self.paginators
        savio_proj_request_object.pending_queryset = \
            self.create_paginator(project_request_pending)

        savio_proj_request_object.complete_queryset = \
            self.create_paginator(project_request_complete)

        savio_proj_request_object.num_pending = project_request_pending.count()

        savio_proj_request_object.title = 'Savio Project Requests'
        savio_proj_request_object.table = \
            'project/project_request/savio/project_request_list_table.html'
        savio_proj_request_object.button_path = \
            'savio-project-pending-request-list'
        savio_proj_request_object.button_text = \
            'Go To Savio Project Requests Main Page'
        savio_proj_request_object.id = 'savio_project_request_section'
        savio_proj_request_object.help_text = \
            'Showing Savio project requests that you requested or requests ' \
            'in which you are the PI for the associated project.'

        return savio_proj_request_object

    def get_vector_project_request(self):
        """Populates a RequestListItem with data for vector project requests"""
        vector_proj_request_object = RequestListItem()
        user = self.request.user

        args = []
        if not self.show_all_requests:
            args.append(Q(pi=user) | Q(requester=user))

        project_request_pending = \
            VectorProjectAllocationRequest.objects.filter(
                status__name__in=['Under Review', 'Approved - Processing'],
                *args).order_by(
                'modified')

        project_request_complete = \
            VectorProjectAllocationRequest.objects.filter(
                status__name__in=['Approved - Complete', 'Denied'],
                *args).order_by(
                'modified')

        vector_proj_request_object.num = self.paginators
        vector_proj_request_object.pending_queryset = \
            self.create_paginator(project_request_pending)

        vector_proj_request_object.complete_queryset = \
            self.create_paginator(project_request_complete)

        vector_proj_request_object.num_pending = project_request_pending.count()

        vector_proj_request_object.title = 'Vector Project Requests'
        vector_proj_request_object.table = \
            'project/project_request/vector/project_request_list_table.html'
        vector_proj_request_object.button_path = \
            'vector-project-pending-request-list'
        vector_proj_request_object.button_text = \
            'Go To Vector Project Requests Main Page'
        vector_proj_request_object.id = 'vector_project_request_section'
        vector_proj_request_object.help_text = \
            'Showing Vector project requests that you requested or requests ' \
            'in which you are the PI for the associated project.'

        return vector_proj_request_object

    def get_project_join_request(self):
        """Populates a RequestListItem with data for project join requests"""
        proj_join_request_object = RequestListItem()
        user = self.request.user

        args = []
        if not self.show_all_requests:
            args.append(Q(project_user__user=user))

        project_join_request_pending = \
            ProjectUserJoinRequest.objects.filter(
                project_user__status__name='Pending - Add',
                *args).order_by('modified')

        project_join_request_complete = \
            ProjectUserJoinRequest.objects.filter(
                project_user__status__name__in=['Active', 'Denied'],
                *args).order_by('modified')

        proj_join_request_object.num = self.paginators
        proj_join_request_object.pending_queryset = \
            self.create_paginator(project_join_request_pending)

        proj_join_request_object.complete_queryset = \
            self.create_paginator(project_join_request_complete)

        proj_join_request_object.num_pending = \
            project_join_request_pending.count()

        proj_join_request_object.title = 'Project Join Requests'
        proj_join_request_object.table = \
            'project/project_join_request_list_table.html'
        proj_join_request_object.button_path = \
            'project-join-request-list'
        proj_join_request_object.button_text = \
            'Go To Project Join Requests Main Page'
        proj_join_request_object.id = 'project_join_request_section'
        proj_join_request_object.help_text = \
            'Showing your project join requests.'

        return proj_join_request_object

    def get_project_renewal_request(self):
        """Populates a RequestListItem with data for project renewal requests"""
        proj_renewal_request_object = RequestListItem()
        user = self.request.user

        args = []
        if not self.show_all_requests:
            args.append(Q(requester=user) | Q(pi=user))

        project_renewal_request_pending = \
            AllocationRenewalRequest.objects.filter(
                status__name__in=['Approved', 'Under Review'], *args).order_by(
                'modified')

        project_renewal_request_complete = \
            AllocationRenewalRequest.objects.filter(
                status__name__in=['Complete', 'Denied'], *args).order_by(
                'modified')

        proj_renewal_request_object.num = self.paginators
        proj_renewal_request_object.pending_queryset = \
            self.create_paginator(project_renewal_request_pending)

        proj_renewal_request_object.complete_queryset = \
            self.create_paginator(project_renewal_request_complete)

        proj_renewal_request_object.num_pending = \
            project_renewal_request_pending.count()

        proj_renewal_request_object.title = 'Project Renewal Requests'
        proj_renewal_request_object.table = \
            'project/project_renewal/project_renewal_request_list_table.html'
        proj_renewal_request_object.button_path = \
            'pi-allocation-renewal-pending-request-list'
        proj_renewal_request_object.button_text = \
            'Go To Project Renewal Requests Main Page'
        proj_renewal_request_object.id = 'project_renewal_request_section'
        proj_renewal_request_object.help_text = \
            'Showing project renewal requests that you requested or requests ' \
            'in which you are the PI for the associated project.'

        return proj_renewal_request_object

    def get_su_purchase_request(self):
        """Populates a RequestListItem with data for SU purchase requests"""
        su_purchase_request_object = RequestListItem()
        user = self.request.user

        su_purchase_request_pending = AllocationAdditionRequest.objects.filter(
            status__name__in=['Under Review']).order_by('modified')

        su_purchase_request_complete = AllocationAdditionRequest.objects.filter(
            status__name__in=['Complete', 'Denied']).order_by('modified')

        if not self.show_all_requests:
            request_ids = [
                r.id for r in su_purchase_request_pending
                if is_user_manager_or_pi_of_project(user, r.project)]
            su_purchase_request_pending = \
                su_purchase_request_pending.filter(id__in=request_ids)

            request_ids = [
                r.id for r in su_purchase_request_complete
                if is_user_manager_or_pi_of_project(user, r.project)]
            su_purchase_request_complete = \
                su_purchase_request_complete.filter(id__in=request_ids)

        su_purchase_request_object.num = self.paginators
        su_purchase_request_object.pending_queryset = \
            self.create_paginator(su_purchase_request_pending)

        su_purchase_request_object.complete_queryset = \
            self.create_paginator(su_purchase_request_complete)

        su_purchase_request_object.num_pending = \
            su_purchase_request_pending.count()

        su_purchase_request_object.title = 'Service Unit Purchase Requests'
        su_purchase_request_object.table = \
            'project/project_allocation_addition/request_list_table.html'
        su_purchase_request_object.button_path = \
            'service-units-purchase-pending-request-list'
        su_purchase_request_object.button_text = \
            'Go To Service Unit Purchase Requests Main Page'
        su_purchase_request_object.id = 'service_unit_purchase_request_section'
        su_purchase_request_object.help_text = \
            'Showing service unit purchase requests in which you are a PI ' \
            'or manager for the associated project.'

        return su_purchase_request_object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        requests = ['cluster_account_request',
                    'project_removal_request',
                    'savio_project_request',
                    'vector_project_request',
                    'project_join_request',
                    'project_renewal_request',
                    'su_purchase_request']

        context['show_all'] = ((self.request.user.is_superuser or
                                self.request.user.is_staff) and
                               self.show_all_requests)

        for request in requests:
            request_obj = eval(f'self.get_{request}()')
            if context['show_all']:
                request_obj.help_text = f'Showing all {request_obj.title} ' \
                                        f'in MyBRC.'
            context[f'{request}_obj'] = request_obj

        context['admin_staff'] = (self.request.user.is_superuser or
                                  self.request.user.is_staff)

        return context
