import datetime
import logging
from datetime import date

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.db.models.query import QuerySet
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import mark_safe
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import FormView, CreateView
from django.core.exceptions import ValidationError
from django import forms

from coldfront.core.utils.mail import send_email_template
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.project.models import (Project, ProjectUser,
                                            ProjectUserStatusChoice)
from coldfront.core.subscription.forms import (SubscriptionAddUserForm,
                                                SubscriptionRemoveUserForm,
                                                SubscriptionForm,
                                                SubscriptionReviewUserForm,
                                                SubscriptionSearchForm,
                                                SubscriptionAttributeDeleteForm,
                                                SubscriptionUpdateForm)
from coldfront.core.subscription.models import (Subscription,
                                                 SubscriptionStatusChoice,
                                                 SubscriptionUser,
                                                 SubscriptionUserStatusChoice,
                                                 SubscriptionAttribute,)
from coldfront.core.subscription.signals import (subscription_activate_user,
                                                  subscription_remove_user)
from coldfront.core.subscription.utils import (generate_guauge_data_from_usage,
                                                get_user_resources)

SUBSCRIPTION_ENABLE_SUBSCRIPTION_RENEWAL = import_from_settings('SUBSCRIPTION_ENABLE_SUBSCRIPTION_RENEWAL', True)
SUBSCRIPTION_DEFAULT_SUBSCRIPTION_LENGTH = import_from_settings('SUBSCRIPTION_DEFAULT_SUBSCRIPTION_LENGTH', 365)

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')
    EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings('EMAIL_OPT_OUT_INSTRUCTION_URL')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_CENTER_NAME = import_from_settings('CENTER_NAME')

ENABLE_PROJECT_REVIEW = import_from_settings('ENABLE_PROJECT_REVIEW', False)


logger = logging.getLogger(__name__)


class SubscriptionDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Subscription
    template_name = 'subscription/subscription_detail.html'
    context_object_name = 'subscription'
    login_url = "/"  # redirect URL if fail test_func

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('subscription.can_view_all_subscriptions'):
            return True

        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        user_can_access_project = subscription_obj.project.projectuser_set.filter(
            user=self.request.user, status__name__in=['Active', 'New',]).exists()

        user_can_access_subscription = subscription_obj.subscriptionuser_set.filter(
            user=self.request.user, status__name__in=['Active', ]).exists()

        if user_can_access_project and user_can_access_subscription:
            return True

        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)
        subscription_users = subscription_obj.subscriptionuser_set.exclude(
            status__name__in=['Removed']).order_by('user__username')

        if self.request.user.is_superuser:
            attributes_with_usage = [attribute for attribute in subscription_obj.subscriptionattribute_set.all() if hasattr(attribute, 'subscriptionattributeusage')]

            attributes_without_usage = [attribute for attribute in subscription_obj.subscriptionattribute_set.all().order_by('subscription_attribute_type__name') if not hasattr(attribute, 'subscriptionattributeusage')]

        else:
            attributes_with_usage = [attribute for attribute in subscription_obj.subscriptionattribute_set.filter(is_private=False) if hasattr(attribute, 'subscriptionattributeusage')]

            attributes_without_usage = [attribute for attribute in subscription_obj.subscriptionattribute_set.filter(is_private=False) if not hasattr(attribute, 'subscriptionattributeusage')]

        guage_data = []
        invalid_attributes = []
        for attribute in attributes_with_usage:
            try:
                guage_data.append(generate_guauge_data_from_usage(attribute.subscription_attribute_type.name,
                                                                  int(attribute.value), int(attribute.subscriptionattributeusage.value)))
            except ValueError:
                logger.error("Subscription attribute '%s' is not an int but has a usage", attribute.subscription_attribute_type.name)
                invalid_attributes.append(attribute)

        for a in invalid_attributes:
            attributes_with_usage.remove(a)


        if self.request.user.is_superuser:
            context['is_allowed_to_update_project'] = True
        elif subscription_obj.project.projectuser_set.filter(user=self.request.user).exists():
            project_user = subscription_obj.project.projectuser_set.get(user=self.request.user)
            if project_user.role.name == 'Manager':
                context['is_allowed_to_update_project'] = True
            else:
                context['is_allowed_to_update_project'] = False
        else:
            context['is_allowed_to_update_project'] = False

        context['guage_data'] = guage_data
        context['attributes_with_usage'] = attributes_with_usage
        context['attributes_without_usage'] = attributes_without_usage

        # Can the user update the project?
        if self.request.user.is_superuser:
            context['is_allowed_to_update_project'] = True
        elif subscription_obj.project.projectuser_set.filter(user=self.request.user).exists():
            project_user = subscription_obj.project.projectuser_set.get(user=self.request.user)
            if project_user.role.name == 'Manager':
                context['is_allowed_to_update_project'] = True
            else:
                context['is_allowed_to_update_project'] = False
        else:
            context['is_allowed_to_update_project'] = False
        context['subscription_users'] = subscription_users


        context['SUBSCRIPTION_ENABLE_SUBSCRIPTION_RENEWAL'] = SUBSCRIPTION_ENABLE_SUBSCRIPTION_RENEWAL
        return context

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        initial_data = {
            'status': subscription_obj.status,
            'end_date': subscription_obj.end_date,
        }

        form = SubscriptionUpdateForm(initial=initial_data)

        context = self.get_context_data()
        context['form'] = form
        context['subscription'] = subscription_obj

        return render(request, self.template_name, context)



    def post(self, request, *args, **kwargs):
        if self.request.user.is_superuser:
            messages.success(request, 'You do not have permission to update the subscription')
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': pk}))

        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        initial_data = {
            'status': subscription_obj.status,
            'end_date': subscription_obj.end_date,
        }

        form = SubscriptionUpdateForm(request.POST, initial=initial_data)

        if form.is_valid():
            form_data = form.cleaned_data
            subscription_obj.end_date = form_data.get('end_date')

            old_status = subscription_obj.status.name
            new_status = form_data.get('status').name

            subscription_obj.status = form_data.get('status')
            subscription_obj.save()

            if EMAIL_ENABLED:
                resource_name = subscription_obj.get_parent_resource
                domain_url = get_domain_url(self.request)
                subscription_url = '{}{}'.format(domain_url, reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))

            if old_status != 'Active' and new_status == 'Active':
                start_date = datetime.datetime.now()
                subscription_obj.start_date = start_date
                subscription_obj.save()
                if EMAIL_ENABLED:
                    template_context = {
                        'center_name': EMAIL_CENTER_NAME,
                        'resource': resource_name,
                        'subscription_url': subscription_url,
                        'signature': EMAIL_SIGNATURE,
                        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
                    }

                    email_receiver_list = []

                    for subscription_user in subscription_obj.subscriptionuser_set.exclude(status__name__in=['Removed', 'Error']):
                        subscription_activate_user.send(sender=self.__class__, subscription_user_pk=subscription_user.pk)
                        if subscription_user.subscription.project.projectuser_set.get(user=subscription_user.user).enable_notifications:
                            email_receiver_list.append(subscription_user.user.email)

                    send_email_template(
                        'Subscription Activated',
                        'email/subscription_activated.txt',
                        template_context,
                        EMAIL_SENDER,
                        email_receiver_list
                    )

            elif old_status != 'Denied' and new_status == 'Denied':
                subscription_obj.start_date = None
                subscription_obj.end_date = None
                subscription_obj.save()
                if EMAIL_ENABLED:
                    template_context = {
                        'center_name': EMAIL_CENTER_NAME,
                        'resource': resource_name,
                        'subscription_url': subscription_url,
                        'signature': EMAIL_SIGNATURE,
                        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
                    }

                    email_receiver_list = []
                    for subscription_user in subscription_obj.project.projectuser_set.all():
                        if subscription_user.enable_notifications:
                            email_receiver_list.append(subscription_user.user.email)

                    send_email_template(
                        'Subscription Denied',
                        'email/subscription_denied.txt',
                        template_context,
                        EMAIL_SENDER,
                        email_receiver_list
                    )

            messages.success(request, 'Subscription updated!')
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': pk}))

class SubscriptionListView(LoginRequiredMixin, ListView):

    model = Subscription
    template_name = 'subscription/subscription_list.html'
    context_object_name = 'subscription_list'
    paginate_by = 25

    def get_queryset(self):

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            elif direction == 'des':
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = 'id'

        subscription_search_form = SubscriptionSearchForm(self.request.GET)

        if subscription_search_form.is_valid():
            data = subscription_search_form.cleaned_data

            if data.get('show_all_subscriptions') and (self.request.user.is_superuser or self.request.user.has_perm('subscription.can_view_all_subscriptions')):
                subscriptions = Subscription.objects.prefetch_related(
                    'project', 'project__pi', 'status',).all().order_by(order_by)
            else:
                subscriptions = Subscription.objects.prefetch_related('project', 'project__pi', 'status',).filter(
                    Q(project__status__name='Active') &
                    Q(project__projectuser__user=self.request.user) &
                    Q(project__projectuser__status__name='Active') &
                    Q(subscriptionuser__user=self.request.user) &
                    Q(subscriptionuser__status__name='Active')
                ).distinct().order_by(order_by)

            # Project Title
            if data.get('project'):
                subscriptions = subscriptions.filter(project__title__icontains=data.get('project'))

            # PI username
            if data.get('pi'):
                subscriptions = subscriptions.filter(project__pi__username__icontains=data.get('pi'))

            # Resource Type
            if data.get('resource_type'):
                subscriptions = subscriptions.filter(resources__resource_type=data.get('resource_type'))

            # Resource Name
            if data.get('resource_name'):
                subscriptions = subscriptions.filter(resources__in=data.get('resource_name'))

            # End Date
            if data.get('end_date'):
                subscriptions = subscriptions.filter(end_date__lt=data.get(
                    'end_date'), status__name='Active').order_by('end_date')

            # Active from now until date
            if data.get('active_from_now_until_date'):
                subscriptions = subscriptions.filter(end_date__gte=date.today())
                subscriptions = subscriptions.filter(end_date__lt=data.get(
                    'active_from_now_until_date'), status__name='Active').order_by('end_date')

            # Status
            if data.get('status'):
                subscriptions = subscriptions.filter(status__in=data.get('status'))

        else:
            subscriptions = Subscription.objects.prefetch_related('project', 'project__pi', 'status',).filter(
                Q(subscriptionuser__user=self.request.user) &
                Q(subscriptionuser__status__name='Active')
            ).order_by(order_by)

        return subscriptions

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        subscriptions_count = self.get_queryset().count()
        context['subscriptions_count'] = subscriptions_count

        subscription_search_form = SubscriptionSearchForm(self.request.GET)

        if subscription_search_form.is_valid():
            context['subscription_search_form'] = subscription_search_form
            data = subscription_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, QuerySet):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele.pk)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['subscription_search_form'] = subscription_search_form
        else:
            filter_parameters = ''
            context['subscription_search_form'] = SubscriptionSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + 'order_by=%s&direction=%s&' % (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        if filter_parameters:
            context['expand_accordion'] = 'show'
        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        subscription_list = context.get('subscription_list')
        paginator = Paginator(subscription_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            subscription_list = paginator.page(page)
        except PageNotAnInteger:
            subscription_list = paginator.page(1)
        except EmptyPage:
            subscription_list = paginator.page(paginator.num_pages)

        return context


class SubscriptionCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = SubscriptionForm
    template_name = 'subscription/subscription_create.html'
    login_url = "/"  # redirect URL if fail test_func

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to create a new subscription.')

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.needs_review:
            messages.error(request, 'You cannot request a new subscription because you have to review your project first.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))


        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(request, 'You cannot request a new subscription to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        context['project'] = project_obj

        user_resources = get_user_resources(self.request.user)
        resources_form_default_quantities = {}
        resources_form_label_texts = {}
        for resource in user_resources:
            if resource.resourceattribute_set.filter(resource_attribute_type__name='quantity_default_value').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='quantity_default_value').value
                resources_form_default_quantities[resource.id] = int(value)
            if resource.resourceattribute_set.filter(resource_attribute_type__name='quantity_label').exists():
                value = resource.resourceattribute_set.get(resource_attribute_type__name='quantity_label').value
                resources_form_label_texts[resource.id] = mark_safe('<strong>{}*</strong>'.format(value))

        context['resources_form_default_quantities'] = resources_form_default_quantities
        context['resources_form_label_texts'] = resources_form_label_texts
        return context

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.request.user, self.kwargs.get('project_pk'), **self.get_form_kwargs())

    def form_valid(self, form):
        form_data = form.cleaned_data
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        resource_obj = form_data.get('resource')
        justification = form_data.get('justification')
        quantity = form_data.get('quantity', 1)

        usernames = form_data.get('users')
        usernames.append(project_obj.pi.username)
        usernames = list(set(usernames))

        users = [User.objects.get(username=username) for username in usernames]
        if project_obj.pi not in users:
            users.append(project_obj.pi)

        subscription_new_status = SubscriptionStatusChoice.objects.get(name='New')
        subscription_obj = Subscription.objects.create(
            project=project_obj,
            justification=justification,
            quantity=quantity,
            status=subscription_new_status
        )
        subscription_obj.resources.add(resource_obj)

        for linked_resource in resource_obj.linked_resources.all():
            subscription_obj.resources.add(linked_resource)

        subscription_user_active_status = SubscriptionUserStatusChoice.objects.get(name='Active')
        for user in users:
            subscription_user_obj = SubscriptionUser.objects.create(
                subscription=subscription_obj,
                user=user,
                status=subscription_user_active_status)

        pi_name = '{} {} ({})'.format(subscription_obj.project.pi.first_name, subscription_obj.project.pi.last_name, subscription_obj.project.pi.username)
        resource_name = subscription_obj.get_parent_resource
        domain_url = get_domain_url(self.request)
        url = '{}{}'.format(domain_url, reverse('subscription-request-list'))


        if EMAIL_ENABLED:
            template_context = {
                'pi': pi_name,
                'resource': resource_name,
                'url': url
            }

            send_email_template(
                'New subscription request: {} - {}'.format(pi_name, resource_name),
                'email/new_subscription_request.txt',
                template_context,
                EMAIL_SENDER,
                [EMAIL_TICKET_SYSTEM_ADDRESS, ]
            )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.kwargs.get('project_pk')})


class SubscriptionAddUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'subscription/subscription_add_users.html'
    login_url = "/"  # redirect URL if fail test_func

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        subscription_obj = get_object_or_404(Subscription, pk=self.kwargs.get('pk'))

        if subscription_obj.project.pi == self.request.user:
            return True

        if subscription_obj.project.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to add users to the subscription.')

    def dispatch(self, request, *args, **kwargs):
        subscription_obj = get_object_or_404(Subscription, pk=self.kwargs.get('pk'))
        if subscription_obj.status.name not in ['Active', 'New', 'Renewal Requested', ]:
            messages.error(request, 'You cannot add users to a subscription with status {}.'.format(
                subscription_obj.status.name))
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_users_to_add(self, subscription_obj):
        active_users_in_project = list(subscription_obj.project.projectuser_set.filter(
            status__name='Active').values_list('user__username', flat=True))
        users_already_in_subscription = list(subscription_obj.subscriptionuser_set.exclude(
            status__name__in=['Removed']).values_list('user__username', flat=True))

        missing_users = list(set(active_users_in_project) - set(users_already_in_subscription))
        missing_users = User.objects.filter(username__in=missing_users).exclude(pk=subscription_obj.project.pi.pk)

        users_to_add = [

            {'username': user.username,
             'first_name': user.first_name,
             'last_name': user.last_name,
             'email': user.email, }

            for user in missing_users
        ]

        return users_to_add

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        users_to_add = self.get_users_to_add(subscription_obj)
        context = {}

        if users_to_add:
            formset = formset_factory(SubscriptionAddUserForm, max_num=len(users_to_add))
            formset = formset(initial=users_to_add, prefix='userform')
            context['formset'] = formset

        context['subscription'] = subscription_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        users_to_add = self.get_users_to_add(subscription_obj)

        formset = formset_factory(SubscriptionAddUserForm, max_num=len(users_to_add))
        formset = formset(request.POST, initial=users_to_add, prefix='userform')

        users_added_count = 0

        if formset.is_valid():

            subscription_user_active_status_choice = SubscriptionUserStatusChoice.objects.get(name='Active')

            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:

                    users_added_count += 1

                    user_obj = User.objects.get(username=user_form_data.get('username'))

                    if subscription_obj.subscriptionuser_set.filter(user=user_obj).exists():
                        subscription_user_obj = subscription_obj.subscriptionuser_set.get(user=user_obj)
                        subscription_user_obj.status = subscription_user_active_status_choice
                        subscription_user_obj.save()
                    else:
                        subscription_user_obj = SubscriptionUser.objects.create(
                            subscription=subscription_obj, user=user_obj, status=subscription_user_active_status_choice)

                    subscription_activate_user.send(sender=self.__class__,
                                                    subscription_user_pk=subscription_user_obj.pk)
            messages.success(request, 'Added {} users to subscription.'.format(users_added_count))
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': pk}))


class SubscriptionRemoveUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'subscription/subscription_remove_users.html'
    login_url = "/"  # redirect URL if fail test_func

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        subscription_obj = get_object_or_404(Subscription, pk=self.kwargs.get('pk'))

        if subscription_obj.project.pi == self.request.user:
            return True

        if subscription_obj.project.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to remove users from subscription.')

    def dispatch(self, request, *args, **kwargs):
        subscription_obj = get_object_or_404(Subscription, pk=self.kwargs.get('pk'))
        if subscription_obj.status.name not in ['Active', 'New', 'Renewal Requested', ]:
            messages.error(request, 'You cannot remove users from a subscription with status {}.'.format(
                subscription_obj.status.name))
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_users_to_remove(self, subscription_obj):
        users_to_remove = list(subscription_obj.subscriptionuser_set.exclude(
            status__name__in=['Removed', 'Error', ]).values_list('user__username', flat=True))

        users_to_remove = User.objects.filter(username__in=users_to_remove).exclude(pk__in=[subscription_obj.project.pi.pk, self.request.user.pk])
        users_to_remove = [

            {'username': user.username,
             'first_name': user.first_name,
             'last_name': user.last_name,
             'email': user.email, }

            for user in users_to_remove
        ]

        return users_to_remove

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        users_to_remove = self.get_users_to_remove(subscription_obj)
        context = {}

        if users_to_remove:
            formset = formset_factory(SubscriptionRemoveUserForm, max_num=len(users_to_remove))
            formset = formset(initial=users_to_remove, prefix='userform')
            context['formset'] = formset

        context['subscription'] = subscription_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        users_to_remove = self.get_users_to_remove(subscription_obj)

        formset = formset_factory(SubscriptionRemoveUserForm, max_num=len(users_to_remove))
        formset = formset(request.POST, initial=users_to_remove, prefix='userform')

        remove_users_count = 0

        if formset.is_valid():
            subscription_user_removed_status_choice = SubscriptionUserStatusChoice.objects.get(name='Removed')
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:

                    remove_users_count += 1

                    user_obj = User.objects.get(username=user_form_data.get('username'))
                    if subscription_obj.project.pi == user_obj:
                        continue

                    subscription_user_obj = subscription_obj.subscriptionuser_set.get(user=user_obj)
                    subscription_user_obj.status = subscription_user_removed_status_choice
                    subscription_user_obj.save()
                    subscription_remove_user.send(sender=self.__class__,
                                                  subscription_user_pk=subscription_user_obj.pk)

            messages.success(request, 'Removed {} users from subscription.'.format(remove_users_count))
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': pk}))



class SubscriptionAttributeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = SubscriptionAttribute
    # fields = ['subscription_attribute_type', 'value', 'is_private', ]
    fields = '__all__'
    template_name = 'subscription/subscription_subscriptionattribute_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        messages.error(self.request, 'You do not have permission to add subscription attributes.')


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)
        context['subscription'] = subscription_obj
        return context


    def get_initial(self):
        initial = super(SubscriptionAttributeCreateView, self).get_initial()
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)
        initial['subscription'] = subscription_obj
        return initial

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        form = super(SubscriptionAttributeCreateView, self).get_form(form_class)
        form.fields['subscription'].widget = forms.HiddenInput()
        return form


    def get_success_url(self):
        return reverse('subscription-detail', kwargs={'pk': self.kwargs.get('pk')})



class SubscriptionAttributeDeleteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'subscription/subscription_subscriptionattribute_delete.html'
    login_url = "/"  # redirect URL if fail test_func

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        messages.error(self.request, 'You do not have permission to delete subscription attributes.')


    def get_subscription_attributes_to_delete(self, subscription_obj):

        subscription_attributes_to_delete = SubscriptionAttribute.objects.filter(subscription=subscription_obj)
        subscription_attributes_to_delete = [

            {'pk': attribute.pk,
             'name': attribute.subscription_attribute_type.name,
             'value': attribute.value,
            }

            for attribute in subscription_attributes_to_delete
        ]

        return subscription_attributes_to_delete

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        subscription_attributes_to_delete = self.get_subscription_attributes_to_delete(subscription_obj)
        context = {}

        if subscription_attributes_to_delete:
            formset = formset_factory(SubscriptionAttributeDeleteForm, max_num=len(subscription_attributes_to_delete))
            formset = formset(initial=subscription_attributes_to_delete, prefix='attributeform')
            context['formset'] = formset
        context['subscription'] = subscription_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        subscription_attributes_to_delete = self.get_subscription_attributes_to_delete(subscription_obj)

        formset = formset_factory(SubscriptionAttributeDeleteForm, max_num=len(subscription_attributes_to_delete))
        formset = formset(request.POST, initial=subscription_attributes_to_delete, prefix='attributeform')

        attributes_deleted_count = 0

        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                if form_data['selected']:

                    attributes_deleted_count += 1

                    subscription_attribute = SubscriptionAttribute.objects.get(pk=form_data['pk'])
                    subscription_attribute.delete()


            messages.success(request, 'Deleted {} attributes from subscription.'.format(attributes_deleted_count))
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': pk}))



class SubscriptionRequestListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'subscription/subscription_request_list.html'
    login_url = "/"

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('subscription.can_review_subscription_requests'):
            return True

        messages.error(self.request, 'You do not have permission to review subscription requests.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subscription_list = Subscription.objects.filter(status__name__in=['New', 'Renewal Requested', ])
        context['subscription_list'] = subscription_list
        context['ENABLE_PROJECT_REVIEW'] = ENABLE_PROJECT_REVIEW
        return context


class SubscriptionActivateRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = "/"

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('subscription.can_review_subscription_requests'):
            return True

        messages.error(self.request, 'You do not have permission to activate a subscription request.')

    def get(self, request, pk):
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        subscription_status_active_obj = SubscriptionStatusChoice.objects.get(name='Active')
        start_date = datetime.datetime.now()
        end_date = datetime.datetime.now() + relativedelta(days=SUBSCRIPTION_DEFAULT_SUBSCRIPTION_LENGTH)

        subscription_obj.status = subscription_status_active_obj
        subscription_obj.start_date = start_date
        subscription_obj.end_date = end_date
        subscription_obj.save()

        messages.success(request, 'Subscription to {} has been ACTIVATED for {} {} ({})'.format(
            subscription_obj.get_parent_resource,
            subscription_obj.project.pi.first_name,
            subscription_obj.project.pi.last_name,
            subscription_obj.project.pi.username)
        )

        resource_name = subscription_obj.get_parent_resource
        domain_url = get_domain_url(self.request)
        subscription_url = '{}{}'.format(domain_url, reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))



        if EMAIL_ENABLED:
            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'resource': resource_name,
                'subscription_url': subscription_url,
                'signature': EMAIL_SIGNATURE,
                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
            }

            email_receiver_list = []

            for subscription_user in subscription_obj.subscriptionuser_set.exclude(status__name__in=['Removed', 'Error']):
                subscription_activate_user.send(sender=self.__class__, subscription_user_pk=subscription_user.pk)
                if subscription_user.subscription.project.projectuser_set.get(user=subscription_user.user).enable_notifications:
                    email_receiver_list.append(subscription_user.user.email)


            send_email_template(
                'Subscription Activated',
                'email/subscription_activated.txt',
                template_context,
                EMAIL_SENDER,
                email_receiver_list
            )

        return HttpResponseRedirect(reverse('subscription-request-list'))


class SubscriptionDenyRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = "/"

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('subscription.can_review_subscription_requests'):
            return True

        messages.error(self.request, 'You do not have permission to deny a subscription request.')

    def get(self, request, pk):
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        subscription_status_denied_obj = SubscriptionStatusChoice.objects.get(name='Denied')


        subscription_obj.status = subscription_status_denied_obj
        subscription_obj.start_date = None
        subscription_obj.end_date = None
        subscription_obj.save()

        messages.success(request, 'Subscription to {} has been DENIED for {} {} ({})'.format(
            subscription_obj.resources.first(),
            subscription_obj.project.pi.first_name,
            subscription_obj.project.pi.last_name,
            subscription_obj.project.pi.username)
        )


        resource_name = subscription_obj.get_parent_resource
        domain_url = get_domain_url(self.request)
        subscription_url = '{}{}'.format(domain_url, reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))


        if EMAIL_ENABLED:
            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'resource': resource_name,
                'subscription_url': subscription_url,
                'signature': EMAIL_SIGNATURE,
                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
            }

            email_receiver_list = []
            for subscription_user in subscription_obj.project.projectuser_set.all():
                if subscription_user.enable_notifications:
                    email_receiver_list.append(subscription_user.user.email)


            send_email_template(
                'Subscription Denied',
                'email/subscription_denied.txt',
                template_context,
                EMAIL_SENDER,
                email_receiver_list
            )

        return HttpResponseRedirect(reverse('subscription-request-list'))


class SubscriptionRenewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'subscription/subscription_renew.html'
    login_url = "/"  # redirect URL if fail test_func

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        subscription_obj = get_object_or_404(Subscription, pk=self.kwargs.get('pk'))

        if subscription_obj.project.pi == self.request.user:
            return True

        if subscription_obj.project.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to renew subscription.')
        return False

    def dispatch(self, request, *args, **kwargs):
        subscription_obj = get_object_or_404(Subscription, pk=self.kwargs.get('pk'))


        if not SUBSCRIPTION_ENABLE_SUBSCRIPTION_RENEWAL:
            messages.error(request, 'Subscription renewal is disabled. Request a new subscription to this resource if you want to continue using it after the active until date.')
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))


        if subscription_obj.status.name not in ['Active', ]:
            messages.error(request, 'You cannot renew a subscription with status {}.'.format(
                subscription_obj.status.name))
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))

        if subscription_obj.project.needs_review:
            messages.error(request, 'You cannot renew your subscription because you have to review your project first.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': subscription_obj.project.pk}))

        if subscription_obj.expires_in > 60:
            messages.error(request, 'It is too soon to review your subscription.')
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_users_in_subscription(self, subscription_obj):
        users_in_subscription = subscription_obj.subscriptionuser_set.exclude(
            status__name__in=['Removed']).exclude(user__pk__in=[subscription_obj.project.pi.pk, self.request.user.pk]).order_by('user__last_name')

        users = [

            {'username': subscription_user.user.username,
             'first_name': subscription_user.user.first_name,
             'last_name': subscription_user.user.last_name,
             'email': subscription_user.user.email, }

            for subscription_user in users_in_subscription
        ]

        return users

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        users_in_subscription = self.get_users_in_subscription(subscription_obj)
        context = {}

        if users_in_subscription:
            formset = formset_factory(SubscriptionReviewUserForm, max_num=len(users_in_subscription))
            formset = formset(initial=users_in_subscription, prefix='userform')
            context['formset'] = formset

        context['subscription'] = subscription_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        users_in_subscription = self.get_users_in_subscription(subscription_obj)

        formset = formset_factory(SubscriptionReviewUserForm, max_num=len(users_in_subscription))
        formset = formset(request.POST, initial=users_in_subscription, prefix='userform')

        subscription_renewal_requested_status_choice = SubscriptionStatusChoice.objects.get(name='Renewal Requested')
        subscription_user_removed_status_choice = SubscriptionUserStatusChoice.objects.get(name='Removed')
        project_user_remove_status_choice = ProjectUserStatusChoice.objects.get(name='Removed')

        subscription_obj.status = subscription_renewal_requested_status_choice
        subscription_obj.save()

        if not users_in_subscription or formset.is_valid():

            if users_in_subscription:
                for form in formset:
                    user_form_data = form.cleaned_data
                    user_obj = User.objects.get(username=user_form_data.get('username'))
                    user_status = user_form_data.get('user_status')

                    if user_status == 'keep_in_project_only':
                        subscription_user_obj = subscription_obj.subscriptionuser_set.get(user=user_obj)
                        subscription_user_obj.status = subscription_user_removed_status_choice
                        subscription_user_obj.save()

                        subscription_remove_user.send(sender=self.__class__, subscription_user_pk=subscription_user_obj.pk)

                    elif user_status == 'remove_from_project':
                        subscription_user_obj = subscription_obj.subscriptionuser_set.get(user=user_obj)
                        subscription_user_obj.status = subscription_user_removed_status_choice
                        subscription_user_obj.save()

                        subscription_remove_user.send(sender=self.__class__, subscription_user_pk=subscription_user_obj.pk)

                        project_user_obj = ProjectUser.objects.get(
                            project=subscription_obj.project,
                            user=user_obj)
                        project_user_obj.status = project_user_remove_status_choice
                        project_user_obj.save()


            pi_name = '{} {} ({})'.format(subscription_obj.project.pi.first_name, subscription_obj.project.pi.last_name, subscription_obj.project.pi.username)
            resource_name = subscription_obj.get_parent_resource
            domain_url = get_domain_url(self.request)
            url = '{}{}'.format(domain_url, reverse('subscription-request-list'))


            if EMAIL_ENABLED:
                template_context = {
                    'pi': pi_name,
                    'resource': resource_name,
                    'url': url
                }

                send_email_template(
                    'Subscription renewed: {} - {}'.format(pi_name, resource_name),
                    'email/subscription_renewed.txt',
                    template_context,
                    EMAIL_SENDER,
                    [EMAIL_TICKET_SYSTEM_ADDRESS, ]
                )

            messages.success(request, 'Subscription renewed successfully')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': subscription_obj.project.pk}))
