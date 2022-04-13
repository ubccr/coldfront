import logging

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.views import View
import datetime
import pprint
from itertools import chain

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError
from django.db.models import Case, CharField, F, Q, Value, When
from django.forms import formset_factory
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.allocation.forms import AllocationSecureDirJoinForm
from coldfront.core.allocation.models import Allocation, \
    SecureDirAddUserRequest, SecureDirAddUserRequestStatusChoice, \
    SecureDirRemoveUserRequest
from coldfront.core.resource.models import Resource
from coldfront.core.utils.mail import send_email, send_email_template


class SecureDirAddUsersView(LoginRequiredMixin,
                            UserPassesTestMixin,
                            TemplateView):
    template_name = 'secure_dir/secure_dir_add_users.html'

    logger = logging.getLogger(__name__)

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        alloc_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        if alloc_obj.project.projectuser_set.filter(
                user=self.request.user,
                role__name='Principal Investigator',
                status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        alloc_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if alloc_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You can only add users to an active allocation.')
            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_users_to_add(self, alloc_obj):
        # part of project's allocation ie active allocationusers
        # cannot already be part of allocation
        # must be active
        # cannot have pending request to join/remove
        savio_compute = Resource.objects.get(name='Savio Compute')
        compute_alloc = Allocation.objects.get(project=alloc_obj.project,
                                               resources=savio_compute)

        # Adding active AllocationUsers from main compute allocation.
        users_to_add = set(alloc_user.user for alloc_user in
                           compute_alloc.allocationuser_set.filter(
                               status__name='Active'))

        # Excluding active users that are already part of the allocation.
        users_to_exclude = set(alloc_user.user for alloc_user in
                               alloc_obj.allocationuser_set.filter(
                                   status__name='Active'))

        # Excluding users that have active join requests.
        users_to_exclude |= \
            set(request.user for request in
                SecureDirAddUserRequest.objects.filter(
                    allocation=alloc_obj,
                    status__name__in=['Pending - Add',
                                      'Processing - Add']))

        # Excluding users that have active removal requests.
        users_to_exclude |= \
            set(request.user for request in
                SecureDirRemoveUserRequest.objects.filter(
                    allocation=alloc_obj,
                    status__name__in=['Pending - Remove',
                                      'Processing - Remove']))

        users_to_add -= users_to_exclude

        user_data_list = []
        for user in users_to_add:
            user_data = {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }
            user_data_list.append(user_data)

        return user_data_list

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        alloc_obj = get_object_or_404(Allocation, pk=pk)

        users_to_add = self.get_users_to_add(alloc_obj)
        context = {}

        if users_to_add:
            formset = formset_factory(
                AllocationSecureDirJoinForm, max_num=len(users_to_add))
            formset = formset(initial=users_to_add, prefix='userform')
            context['formset'] = formset

        context['allocation'] = alloc_obj

        context['can_add_users'] = False
        if self.request.user.is_superuser:
            context['can_add_users'] = True

        if alloc_obj.project.projectuser_set.filter(
                user=self.request.user,
                role__name='Principal Investigator',
                status__name='Active').exists():
            context['can_add_users'] = True

        resource_type = 'scratch2' if \
            alloc_obj.resources.filter(name__icontains='Scratch').exists() \
            else 'group'
        context['title'] = f'secure {resource_type} directory for ' \
                           f'{alloc_obj.project.name}'

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        alloc_obj = get_object_or_404(Allocation, pk=pk)

        allowed_to_approve_users = False
        if alloc_obj.project.projectuser_set.filter(
                user=self.request.user,
                role__name='Principal Investigator',
                status__name='Active').exists():
            allowed_to_approve_users = True

        if self.request.user.is_superuser:
            allowed_to_approve_users = True

        if not allowed_to_approve_users:
            message = 'You do not have permission to view the this page.'
            messages.error(request, message)

            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': pk}))

        users_to_add = self.get_users_to_add(alloc_obj)

        formset = formset_factory(
            AllocationSecureDirJoinForm, max_num=len(users_to_add))
        formset = formset(
            request.POST, initial=users_to_add, prefix='userform')

        reviewed_users_count = 0

        # TODO: how does this decision variable get populated?
        decision = request.POST.get('decision', None)
        if decision != 'add':
            return HttpResponse('', status=400)

        if formset.is_valid():
            pending_status = \
                SecureDirAddUserRequestStatusChoice.objects.get(
                    name='Pending - Add')

            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:
                    reviewed_users_count += 1
                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))

                    # Create a new SecureDirAddUserRequest for the user.
                    secure_dir_request = SecureDirAddUserRequest.objects.create(
                        user=user_obj,
                        allocation=alloc_obj,
                        status=pending_status
                    )

                    # TODO: do we email admins? Probably

            # TODO: alter message or is it already informative enough?
            message = (
                f'Successfully requested secure directory access for '
                f'{reviewed_users_count} user'
                f'{"s" if reviewed_users_count > 1 else ""}. BRC staff '
                f'have been notified.')
            messages.success(request, message)

        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(
            reverse('allocation-detail', kwargs={'pk': pk}))
