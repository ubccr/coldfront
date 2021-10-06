from coldfront.core.allocation.models import AllocationRenewalRequest

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from django.views.generic import TemplateView

import logging


logger = logging.getLogger(__name__)


class AllocationRenewalRequestListView(LoginRequiredMixin, TemplateView):
    template_name = 'project/project_renewal/project_renewal_request_list.html'
    login_url = '/'
    completed = False

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
        return AllocationRenewalRequest.objects.order_by(order_by)

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser, show all such requests. Otherwise, show only those
        for which the user is a requester or PI."""
        context = super().get_context_data(**kwargs)

        args, kwargs = [], {}

        request_list = self.get_queryset()
        user = self.request.user
        if not user.is_superuser:
            args.append(Q(requester=user) | Q(pi=user))
        if self.completed:
            status__name__in = ['Approved', 'Complete', 'Denied']
        else:
            status__name__in = ['Under Review']
        kwargs['status__name__in'] = status__name__in
        context['renewal_request_list'] = request_list.filter(*args, **kwargs)
        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context


class AllocationRenewalRequestDetailView(LoginRequiredMixin,
                                         UserPassesTestMixin, DetailView):
    model = AllocationRenewalRequest
    template_name = (
        'project/project_renewal/project_renewal_request_detail.html')
    login_url = '/'
    context_object_name = 'renewal_request'

    request_obj = None

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        if (self.request.user == self.request_obj.requester or
                self.request.user == self.request.pi):
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(
            AllocationRenewalRequest.objects.prefetch_related(
                'pi', 'requester'), pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        pass
