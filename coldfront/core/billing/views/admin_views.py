from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.base import TemplateView

from coldfront.core.billing.forms import BillingIDUsagesSearchForm
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.utils.queries import get_billing_id_usages


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
        billing_activity = data.get('billing_id', None)
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
            project_name = allocation_attribute.allocation.project.name
            context['project_default_usages'].append(
                {'project_name': project_name, 'full_id': full_id})

        for allocation_user_attribute in usages.recharge:
            pk = int(allocation_user_attribute.value)
            if billing_id:
                full_id = billing_id
            elif pk in full_id_by_billing_activity_pk:
                full_id = full_id_by_billing_activity_pk[pk]
            else:
                full_id = BillingActivity.objects.get(pk=pk).full_id()
                full_id_by_billing_activity_pk[pk] = full_id
            project_name = allocation_user_attribute.allocation.project.name
            username = allocation_user_attribute.allocation_user.user.username
            context['recharge_usages'].append(
                {'project_name': project_name, 'username': username,
                 'full_id': full_id})

        for user_profile in usages.user_account:
            full_id = user_profile.billing_activity.full_id()
            username = user_profile.user.username
            context['user_account_usages'].append(
                {'username': username, 'full_id': full_id})

        return context
