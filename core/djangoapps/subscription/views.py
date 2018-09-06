import datetime
from datetime import date

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.db.models.query import QuerySet
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.html import mark_safe
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import FormView

from common.djangolibs.utils import import_from_settings
from core.djangoapps.project.models import Project, ProjectUserStatusChoice, ProjectUser
from core.djangoapps.subscription.forms import (SubscriptionAddUserForm,
                                                SubscriptionDeleteUserForm,
                                                SubscriptionForm,
                                                SubscriptionSearchForm,
                                                SubscriptionReviewUserForm)
from core.djangoapps.subscription.models import (Subscription,
                                                 SubscriptionStatusChoice,
                                                 SubscriptionUser,
                                                 SubscriptionUserStatusChoice)
from core.djangoapps.subscription.signals import (subscription_activate_user,
                                                  subscription_remove_user)
from core.djangoapps.subscription.utils import (generate_guauge_data_from_usage,
                                                get_user_resources)

from django.template.loader import render_to_string
from common.djangolibs.utils import get_domain_url

EMAIL_DEVELOPMENT_EMAIL_LIST = import_from_settings('EMAIL_DEVELOPMENT_EMAIL_LIST')
EMAIL_SUBJECT_PREFIX = import_from_settings('EMAIL_SUBJECT_PREFIX')
EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')
EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings('EMAIL_OPT_OUT_INSTRUCTION_URL')
EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
EMAIL_CENTER_NAME = import_from_settings('EMAIL_CENTER_NAME')


class SubscriptionDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
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

        subscription_obj = self.get_object()

        user_can_access_project = subscription_obj.project.projectuser_set.filter(
            user=self.request.user, status__name='Active').exists()

        user_can_access_subscription = subscription_obj.subscriptionuser_set.filter(
            user=self.request.user, status__name__in=['Active', 'Pending Add']).exists()

        if user_can_access_project and user_can_access_subscription:
            return True

        messages.error(self.request, 'You do not have permission to view the previous page.')
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # subscription_obj = self.get_object()
        subscription_users = self.object.subscriptionuser_set.filter(
            status__name__in=['Active', 'Pending - Add', 'New', ]).order_by('user__username')

        if self.request.user.is_superuser:
            attributes_with_usage = [attribute for attribute in self.object.subscriptionattribute_set.all() if hasattr(attribute, 'subscriptionattributeusage')]

            attributes_without_usage = [attribute for attribute in self.object.subscriptionattribute_set.all() if not hasattr(attribute, 'subscriptionattributeusage')]

        else:
            attributes_with_usage = [attribute for attribute in self.object.subscriptionattribute_set.filter(is_private=False) if hasattr(attribute, 'subscriptionattributeusage')]

            attributes_without_usage = [attribute for attribute in self.object.subscriptionattribute_set.filter(is_private=False) if not hasattr(attribute, 'subscriptionattributeusage')]

        guage_data = []
        for attribute in attributes_with_usage:
            guage_data.append(generate_guauge_data_from_usage(attribute.subscription_attribute_type.name,
                                                              int(attribute.value), int(attribute.subscriptionattributeusage.value)))

        context['guage_data'] = guage_data

        context['attributes_with_usage'] = attributes_with_usage
        context['attributes_without_usage'] = attributes_without_usage

        # Can the user update the project?
        if self.request.user.is_superuser:
            context['is_allowed_to_update_project'] = True
        elif self.object.project.projectuser_set.filter(user=self.request.user).exists():
            project_user = self.object.project.projectuser_set.get(user=self.request.user)
            if project_user.role.name == 'Manager':
                context['is_allowed_to_update_project'] = True
            else:
                context['is_allowed_to_update_project'] = False
        else:
            context['is_allowed_to_update_project'] = False
        context['subscription_users'] = subscription_users
        return context


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
                    Q(status__name__in=['Active', 'Approved', 'Denied', 'New', 'Pending', ]) &
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

            # Active Until
            if data.get('active_until'):
                subscriptions = subscriptions.filter(active_until__lt=data.get(
                    'active_until'), status__name='Active').order_by('active_until')

            # Active from now until date
            if data.get('active_from_now_until_date'):
                subscriptions = subscriptions.filter(active_until__gte=date.today())
                subscriptions = subscriptions.filter(active_until__lt=data.get(
                    'active_from_now_until_date'), status__name='Active').order_by('active_until')

            # Status
            if data.get('status'):
                subscriptions = subscriptions.filter(status__in=data.get('status'))

        else:
            subscriptions = Subscription.objects.prefetch_related('project', 'project__pi', 'status',).filter(
                Q(status__name__in=['Active', 'Pending', 'New', 'Approved']) &
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

        if project_obj.last_project_review and project_obj.last_project_review.status.name == 'Pending':
            messages.error(request, 'You cannot request a new subscription because your project review is in pending state.')
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
            print('test')
            users.append(project_obj.pi)

        active_until = datetime.datetime.now() + relativedelta(years=1)
        subscription_new_status = SubscriptionStatusChoice.objects.get(name='New')
        subscription_obj = Subscription.objects.create(
            project=project_obj,
            justification=justification,
            quantity=quantity,
            active_until=active_until,
            status=subscription_new_status
        )
        subscription_obj.resources.add(resource_obj)

        for linked_resource in resource_obj.linked_resources.all():
            subscription_obj.resources.add(linked_resource)

        subscription_user_active_status = SubscriptionUserStatusChoice.objects.get(name='Active')
        subscription_user_pending_add_status_choice = SubscriptionUserStatusChoice.objects.get(name='Pending - Add')
        for user in users:
            subscription_user_obj = SubscriptionUser.objects.create(
                subscription=subscription_obj,
                user=user,
                status=subscription_user_pending_add_status_choice)
            subscription_activate_user.send(sender=self.__class__,
                                            subscription_user_pk=subscription_user_obj.pk)

        pi_name = '{} {} ({})'.format(subscription_obj.project.pi.first_name, subscription_obj.project.pi.last_name, subscription_obj.project.pi.username)
        resource_name = subscription_obj.get_parent_resource
        domain_url = get_domain_url(self.request)
        url = '{}{}'.format(domain_url, reverse('subscription-request-list'))

        template_context = {
            'pi': pi_name,
            'resource': resource_name,
            'url': url
        }

        email_subject = EMAIL_SUBJECT_PREFIX + ' New subscription request: {} - {}'.format(pi_name, resource_name)
        email_body = render_to_string('email/new_subscription_request.txt', template_context)
        email_sender = EMAIL_SENDER

        if settings.DEBUG and settings.DEVELOP:
            email_receiver_list = EMAIL_DEVELOPMENT_EMAIL_LIST
        else:
            email_receiver_list = [EMAIL_TICKET_SYSTEM_ADDRESS, ]

        send_mail(email_subject, email_body, email_sender, email_receiver_list, fail_silently=False)

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
        if subscription_obj.status.name not in ['Active', 'Approved', 'New', 'Pending', ]:
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
            subscription_user_pending_add_status_choice = SubscriptionUserStatusChoice.objects.get(name='Pending - Add')

            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:

                    users_added_count += 1

                    user_obj = User.objects.get(username=user_form_data.get('username'))

                    if subscription_obj.subscriptionuser_set.filter(user=user_obj).exists():
                        subscription_user_obj = subscription_obj.subscriptionuser_set.get(user=user_obj)
                        subscription_user_obj.status = subscription_user_pending_add_status_choice
                        subscription_user_obj.save()
                    else:
                        subscription_user_obj = SubscriptionUser.objects.create(
                            subscription=subscription_obj, user=user_obj, status=subscription_user_pending_add_status_choice)

                    subscription_activate_user.send(sender=self.__class__,
                                                    subscription_user_pk=subscription_user_obj.pk)
            messages.success(request, 'Added {} users to subscription.'.format(users_added_count))
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': pk}))


class SubscriptionDeleteUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'subscription/subscription_delete_users.html'
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

        messages.error(self.request, 'You do not have permission to delete users from subscription.')

    def dispatch(self, request, *args, **kwargs):
        subscription_obj = get_object_or_404(Subscription, pk=self.kwargs.get('pk'))
        if subscription_obj.status.name not in ['Active', 'New', 'Pending', 'Approved', ]:
            messages.error(request, 'You cannot delete users from a subscription with status {}.'.format(
                subscription_obj.status.name))
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_users_to_delete(self, subscription_obj):
        users_to_delete = list(subscription_obj.subscriptionuser_set.filter(
            status__name__in=['Active', 'Pending - Add']).values_list('user__username', flat=True))

        users_to_delete = User.objects.filter(username__in=users_to_delete).exclude(pk=subscription_obj.project.pi.pk)
        users_to_delete = [

            {'username': user.username,
             'first_name': user.first_name,
             'last_name': user.last_name,
             'email': user.email, }

            for user in users_to_delete
        ]

        return users_to_delete

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        users_to_delete = self.get_users_to_delete(subscription_obj)
        context = {}

        if users_to_delete:
            formset = formset_factory(SubscriptionDeleteUserForm, max_num=len(users_to_delete))
            formset = formset(initial=users_to_delete, prefix='userform')
            context['formset'] = formset

        context['subscription'] = subscription_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        users_to_delete = self.get_users_to_delete(subscription_obj)

        formset = formset_factory(SubscriptionDeleteUserForm, max_num=len(users_to_delete))
        formset = formset(request.POST, initial=users_to_delete, prefix='userform')

        delete_users_count = 0

        if formset.is_valid():
            subscription_user_removed_status_choice = SubscriptionUserStatusChoice.objects.get(name='Removed')
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:

                    delete_users_count += 1

                    user_obj = User.objects.get(username=user_form_data.get('username'))
                    if subscription_obj.pi == user_obj:
                        continue

                    subscription_user_obj = subscription_obj.subscriptionuser_set.get(user=user_obj)
                    subscription_user_obj.status = subscription_user_removed_status_choice
                    subscription_user_obj.save()
                    subscription_remove_user.send(sender=self.__class__,
                                                  subscription_user_pk=subscription_user_obj.pk)

            messages.success(request, 'Deleted {} users from subscription.'.format(delete_users_count))
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
        subscription_list = Subscription.objects.filter(status__name__in=['New', 'Pending'])
        context['subscription_list'] = subscription_list
        return context


class SubscriptionApproveRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = "/"

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('subscription.can_review_subscription_requests'):
            return True

        messages.error(self.request, 'You do not have permission to approve a subscription request.')

    def get(self, request, pk):
        subscription_obj = get_object_or_404(Subscription, pk=pk)

        subscription_status_approved_obj = SubscriptionStatusChoice.objects.get(name='Approved')
        subscription_obj.status = subscription_status_approved_obj
        subscription_obj.save()

        messages.success(request, 'Subscription to {} has been APPROVED for {} {} ({})'.format(
            subscription_obj.get_parent_resource,
            subscription_obj.project.pi.first_name,
            subscription_obj.project.pi.last_name,
            subscription_obj.project.pi.username)
        )

        resource_name = subscription_obj.get_parent_resource
        domain_url = get_domain_url(self.request)
        subscription_url = '{}{}'.format(domain_url, reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))

        template_context = {
            'center_name': EMAIL_CENTER_NAME,
            'resource': resource_name,
            'subscription_url': subscription_url,
            'signature': EMAIL_SIGNATURE,
            'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
        }

        email_subject = EMAIL_SUBJECT_PREFIX + ' Subscription Activated'
        email_body = render_to_string('email/subscription_activated.txt', template_context)
        email_sender = EMAIL_SENDER

        if settings.DEBUG and settings.DEVELOP:
            email_receiver_list = EMAIL_DEVELOPMENT_EMAIL_LIST
        else:
            email_receiver_list = []
            for subscription_user in subscription_obj.project.projectuser_set.all():
                if subscription_user.enable_notifications:
                    email_receiver_list.append(subscription_user.user.email)

        send_mail(email_subject, email_body, email_sender, email_receiver_list, fail_silently=False)

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

        template_context = {
            'center_name': EMAIL_CENTER_NAME,
            'resource': resource_name,
            'subscription_url': subscription_url,
            'signature': EMAIL_SIGNATURE,
            'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
        }

        email_subject = EMAIL_SUBJECT_PREFIX + ' Subscription Denied'
        email_body = render_to_string('email/subscription_denied.txt', template_context)
        email_sender = EMAIL_SENDER

        if settings.DEBUG and settings.DEVELOP:
            email_receiver_list = EMAIL_DEVELOPMENT_EMAIL_LIST
        else:
            email_receiver_list = []
            for subscription_user in subscription_obj.project.projectuser_set.all():
                if subscription_user.enable_notifications:
                    email_receiver_list.append(subscription_user.user.email)

        send_mail(email_subject, email_body, email_sender, email_receiver_list, fail_silently=False)

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

        if subscription_obj.status.name not in ['Active', ]:
            messages.error(request, 'You cannot renew a subscription with status {}.'.format(
                subscription_obj.status.name))
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))

        if subscription_obj.project.needs_review:
            messages.error(request, 'You cannot request a new subscription because you have to review your project first.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': subscription_obj.project.pk}))

        if subscription_obj.project.last_project_review and subscription_obj.project.last_project_review.status.name == 'Pending':
            messages.error(request, 'You cannot request a new subscription because your project review is in pending state.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': subscription_obj.project.pk}))

        if subscription_obj.expires_in > 60:
            messages.error(request, 'It is too soon to review your subscription.')
            return HttpResponseRedirect(reverse('subscription-detail', kwargs={'pk': subscription_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_users_in_subscription(self, subscription_obj):
        users_in_subscription = subscription_obj.subscriptionuser_set.exclude(
            status__name__in=['Removed']).exclude(user=subscription_obj.project.pi).order_by('user__last_name')

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
        old_subscription_obj = get_object_or_404(Subscription, pk=pk)

        users_in_subscription = self.get_users_in_subscription(old_subscription_obj)

        formset = formset_factory(SubscriptionReviewUserForm, max_num=len(users_in_subscription))
        formset = formset(request.POST, initial=users_in_subscription, prefix='userform')

        if not users_in_subscription or formset.is_valid():
            subscription_pending_status_choice = SubscriptionStatusChoice.objects.get(name='Pending')
            subscription_inactive_status_choice = SubscriptionStatusChoice.objects.get(name='Inactive (Renewed)')

            subscription_user_active_status_choice = SubscriptionUserStatusChoice.objects.get(name='Active')

            project_user_remove_status_choice = ProjectUserStatusChoice.objects.get(name='Removed')

            active_until = datetime.datetime.now() + relativedelta(years=1)

            new_subscription_obj = Subscription.objects.create(
                project=old_subscription_obj.project,
                justification=old_subscription_obj.justification,
                quantity=old_subscription_obj.quantity,
                active_until=active_until,
                status=subscription_pending_status_choice
            )

            for resource in old_subscription_obj.resources.all():
                new_subscription_obj.resources.add(resource)

            # Add PI
            subscription_user_obj = SubscriptionUser.objects.create(
                subscription=new_subscription_obj,
                user=old_subscription_obj.project.pi,
                status=subscription_user_active_status_choice)
            subscription_activate_user.send(sender=self.__class__, subscription_user_pk=subscription_user_obj.pk)

            if users_in_subscription:
                for form in formset:
                    user_form_data = form.cleaned_data

                    user_obj = User.objects.get(username=user_form_data.get('username'))

                    user_status = user_form_data.get('user_status')

                    if user_status == 'keep_in_subscription_and_project':
                        subscription_user_obj = SubscriptionUser.objects.create(
                            subscription=new_subscription_obj,
                            user=user_obj,
                            status=subscription_user_active_status_choice)
                        subscription_activate_user.send(
                            sender=self.__class__, subscription_user_pk=subscription_user_obj.pk)

                    elif user_status == 'keep_in_project_only':
                        continue

                    elif user_status == 'remove_from_project':
                        project_user_obj = ProjectUser.objects.get(
                            project=old_subscription_obj.project,
                            user=user_obj)
                        project_user_obj.status = project_user_remove_status_choice
                        project_user_obj.save()

            old_subscription_obj.status = subscription_inactive_status_choice
            old_subscription_obj.save()

            pi_name = '{} {} ({})'.format(new_subscription_obj.project.pi.first_name, new_subscription_obj.project.pi.last_name, new_subscription_obj.project.pi.username)
            resource_name = new_subscription_obj.get_parent_resource
            domain_url = get_domain_url(self.request)
            url = '{}{}'.format(domain_url, reverse('subscription-request-list'))
            template_context = {
                'pi': pi_name,
                'resource': resource_name,
                'url': url
            }

            email_subject = EMAIL_SUBJECT_PREFIX + ' Subscription renewed: {} - {}'.format(pi_name, resource_name)
            email_body = render_to_string('email/subscription_renewed.txt', template_context)
            email_sender = EMAIL_SENDER

            if settings.DEBUG and settings.DEVELOP:
                email_receiver_list = EMAIL_DEVELOPMENT_EMAIL_LIST
            else:
                email_receiver_list = [EMAIL_TICKET_SYSTEM_ADDRESS, ]

            send_mail(email_subject, email_body, email_sender, email_receiver_list, fail_silently=False)

            messages.success(request, 'Subscription renewed successfully')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': new_subscription_obj.project.pk}))
