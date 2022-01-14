from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.project.utils_.permissions_utils import is_user_manager_or_pi_of_project

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class AllocationAdditionRequestListView(LoginRequiredMixin, TemplateView):
    """A view that lists pending or completed requests to purchase more
    Service Units under Projects."""

    template_name = 'project/project_allocation_addition/request_list.html'
    login_url = '/'
    completed = False

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser or has the appropriate permissions, show all such
        requests. Otherwise, show only those for Projects of which the
        user is a PI or manager."""
        context = super().get_context_data(**kwargs)

        if self.completed:
            status__name__in = ['Complete', 'Denied']
        else:
            status__name__in = ['Under Review']
        order_by = self.get_order_by()
        request_list = AllocationAdditionRequest.objects.filter(
            status__name__in=status__name__in).order_by(order_by)

        user = self.request.user
        permission = 'allocation.view_allocationadditionrequest'
        if not (user.is_superuser or user.has_perm(permission)):
            request_ids = [
                r.id for r in request_list
                if is_user_manager_or_pi_of_project(user, r.project)]
            request_list = AllocationAdditionRequest.objects.filter(
                id__in=request_ids).order_by(order_by)

        context['request_list'] = request_list
        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context

    def get_order_by(self):
        """Return a string to be used to order results using the field
        and direction specified by the user. If not provided, default to
        sorting by ascending ID."""
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
        return order_by
