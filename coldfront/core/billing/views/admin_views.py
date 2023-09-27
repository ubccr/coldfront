import logging

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.billing.forms import BillingIDCreationForm
from coldfront.core.billing.forms import BillingIDSetProjectDefaultForm
from coldfront.core.billing.forms import BillingIDSetRechargeForm
from coldfront.core.billing.forms import BillingIDSetUserAccountForm
from coldfront.core.billing.forms import BillingIDUsagesSearchForm
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.utils.billing_activity_managers import ProjectBillingActivityManager
from coldfront.core.billing.utils.billing_activity_managers import ProjectUserBillingActivityManager
from coldfront.core.billing.utils.billing_activity_managers import UserBillingActivityManager
from coldfront.core.billing.utils.queries import get_billing_id_usages
from coldfront.core.billing.utils.queries import get_or_create_billing_activity_from_full_id
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser


logger = logging.getLogger(__name__)


class BillingIDCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):

    form_class = BillingIDCreationForm
    template_name = 'billing/billing_id_create.html'

    def test_func(self):
        return self.request.user.is_superuser

    def form_valid(self, form):
        billing_id = form.cleaned_data.get('billing_id')
        try:
            # The form checks that it does not exist.
            get_or_create_billing_activity_from_full_id(billing_id)
        except Exception as e:
            logger.exception(
                f'Failed to create BillingActivity for {billing_id}. '
                f'Details:\n{e}')
            messages.error(
                self.request,
                'Unexpected failure. Please contact an administrator.')
        else:
            log_message = (
                f'Administrator {self.request.user} created a BillingActivity '
                f'for {billing_id}')
            message = f'Created {billing_id}'
            if form.is_billing_id_invalid:
                # The form would only be valid if the user chose ignore_invalid.
                invalid_note = ' (ignoring that it was invalid)'
                log_message += invalid_note
                message += invalid_note
            log_message += '.'
            message += '.'
            logger.info(log_message)
            messages.success(self.request, message)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('billing-id-usages')


class BillingIDSetView(LoginRequiredMixin, UserPassesTestMixin, FormView):

    template_name = 'billing/billing_id_set.html'

    _allowed_billing_id_types_and_labels = {
        'project_default': 'Project Default',
        'recharge': 'Recharge',
        'user_account': 'User Account',
    }

    def __init__(self, *args, **kwargs):
        self._billing_id_type = None
        self._billing_activity_manager = None
        self._project = None
        self._user = None
        super().__init__(*args, **kwargs)

    def test_func(self):
        return self.request.user.is_superuser

    def dispatch(self, request, *args, **kwargs):
        self._billing_id_type = kwargs['billing_id_type']
        if (self._billing_id_type not in
                self._allowed_billing_id_types_and_labels):
            messages.error(request, 'Invalid billing ID type.')
            return redirect(self.get_success_url())
        self._billing_activity_manager = self._set_billing_activity_manager()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        billing_activity = form.cleaned_data.get('billing_activity')
        billing_id = billing_activity.full_id()
        entity_str = self._billing_activity_manager.entity_str
        prev_billing_id = 'None'
        if self._billing_activity_manager.billing_activity:
            prev_billing_id = \
                self._billing_activity_manager.billing_activity.full_id()
        try:
            self._billing_activity_manager.billing_activity = billing_activity
        except Exception as e:
            logger.exception(
                f'Failed to update BillingActivity of type '
                f'{self._billing_id_type} for {entity_str} from '
                f'{prev_billing_id} to {billing_id}. Details:\n{e}')
            messages.error(
                self.request,
                'Unexpected failure. Please contact an administrator.')
        else:
            log_message = (
                f'Administrator {self.request.user} updated the '
                f'BillingActivity of type {self._billing_id_type} for '
                f'{entity_str} from {prev_billing_id} to {billing_id}')
            billing_id_type_label = self._allowed_billing_id_types_and_labels[
                self._billing_id_type]
            message = (
                f'Updated the {billing_id_type_label} Project ID for '
                f'{entity_str} from {prev_billing_id} to {billing_id}')
            if form.is_billing_id_invalid:
                # The form would only be valid if the user chose ignore_invalid.
                invalid_note = f' (ignoring that it was invalid)'
                log_message += invalid_note
                message += invalid_note
            log_message += '.'
            message += '.'
            logger.info(log_message)
            messages.success(self.request, message)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['billing_id_type_label'] = \
            self._allowed_billing_id_types_and_labels[self._billing_id_type]
        return context

    def get_form_class(self):
        if self._billing_id_type == 'project_default':
            return BillingIDSetProjectDefaultForm
        elif self._billing_id_type == 'recharge':
            return BillingIDSetRechargeForm
        else:
            return BillingIDSetUserAccountForm

    def get_initial(self):
        initial = super().get_initial()
        billing_activity = self._billing_activity_manager.billing_activity
        if billing_activity is not None:
            initial['billing_activity'] = billing_activity
        if self._billing_id_type == 'project_default':
            initial['project'] = self._project.name
        elif self._billing_id_type == 'recharge':
            initial['project'] = self._project.name
            initial['user'] = self._user.username
        else:
            initial['user'] = self._user.username
        return initial

    def get_success_url(self):
        if 'next' in self.request.POST:
            return self.request.POST['next']
        return reverse('billing-id-usages')

    def _set_billing_activity_manager(self):
        """Store a concrete instance of BillingActivityManager based on
        the billing ID type and required parameters in the query string.
            - For project_default, a valid Project (PK) must be
              specified.
            - For recharge, a valid Project (PK) and a valid User (PK)
              must be specified, and there must be a corresponding
              ProjectUser.
            - For user_account, a valid User (PK) must be specified.

        Also store the relevant Project and User objects as needed.
        """
        if self._billing_id_type == 'project_default':
            project_pk_str = self.request.GET.get('project', '').strip()
            try:
                self._project = Project.objects.get(pk=int(project_pk_str))
            except Project.DoesNotExist:
                raise ValueError('Invalid project.')
            return ProjectBillingActivityManager(self._project)
        elif self._billing_id_type == 'recharge':
            project_pk_str = self.request.GET.get('project', '').strip()
            self._project = Project.objects.get(pk=int(project_pk_str))
            user_pk_str = self.request.GET.get('user', '').strip()
            self._user = User.objects.get(pk=int(user_pk_str))
            project_user = ProjectUser.objects.get(
                project=self._project, user=self._user)
            return ProjectUserBillingActivityManager(project_user)
        else:
            user_pk_str = self.request.GET.get('user', '').strip()
            self._user = User.objects.get(pk=int(user_pk_str))
            return UserBillingActivityManager(self._user)


class BillingIDUsagesSearchView(LoginRequiredMixin, UserPassesTestMixin,
                                TemplateView):
    """Search for usages of billing IDs."""

    template_name = 'billing/billing_id_usages_search.html'

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['project_default_usages'] = []
        context['recharge_usages'] = []
        context['user_account_usages'] = []

        search_form = BillingIDUsagesSearchForm(self.request.GET)
        context['search_form'] = search_form
        if not search_form.is_valid():
            return context
        data = search_form.cleaned_data
        usage_kwargs = {'full_id': None, 'project_obj': None, 'user_obj': None}
        billing_activity = data.get('billing_activity', None)
        if billing_activity:
            billing_id = billing_activity.full_id()
            usage_kwargs['full_id'] = billing_id
        else:
            billing_id = ''
        usage_kwargs['project_obj'] = data.get('project', None)
        usage_kwargs['user_obj'] = data.get('user', None)
        usages = get_billing_id_usages(**usage_kwargs)

        # TODO: Much of this is duplicated from the billing_ids command.
        #  Refactor.
        full_id_by_billing_activity_pk = {}

        for allocation_attribute in usages.project_default:
            pk = int(allocation_attribute.value)
            if billing_id:
                full_id = billing_id
            elif pk in full_id_by_billing_activity_pk:
                full_id = full_id_by_billing_activity_pk[pk]
            else:
                full_id = BillingActivity.objects.get(pk=pk).full_id()
                full_id_by_billing_activity_pk[pk] = full_id
            project = allocation_attribute.allocation.project
            context['project_default_usages'].append({
                'project_pk': project.pk,
                'project_name': project.name,
                'full_id': full_id,
            })

        for allocation_user_attribute in usages.recharge:
            pk = int(allocation_user_attribute.value)
            if billing_id:
                full_id = billing_id
            elif pk in full_id_by_billing_activity_pk:
                full_id = full_id_by_billing_activity_pk[pk]
            else:
                full_id = BillingActivity.objects.get(pk=pk).full_id()
                full_id_by_billing_activity_pk[pk] = full_id
            project = allocation_user_attribute.allocation.project
            user = allocation_user_attribute.allocation_user.user
            context['recharge_usages'].append(
                {
                    'project_pk': project.pk,
                    'project_name': project.name,
                    'user_pk': user.pk,
                    'username': user.username,
                    'full_id': full_id,
                })

        for user_profile in usages.user_account:
            if user_profile.billing_activity:
                full_id = user_profile.billing_activity.full_id()
            else:
                full_id = 'N/A'
            user = user_profile.user
            context['user_account_usages'].append(
                {
                    'user_pk': user.pk,
                    'username': user.username,
                    'full_id': full_id,
                })

        # Once the linked form is submitted, redirect back to this page, with
        # the same parameters, for further editing.
        next_url = (
            f'{reverse("billing-id-usages")}?{urlencode(self.request.GET)}')
        context['next_url_parameter'] = urlencode({'next': next_url})

        return context
