from django.db.models import OuterRef, Subquery

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationAttributeUsage,
)
from coldfront.core.project.models import Project


class BillingResultSet:
    def retrieve_billing_result_set(billing_cycle, begin_billing, end_billing):
        # Virtual Onsite 06/24/2025
        # currently allocations that start or end in the middle of the month are intentionally filtered out
        allocation_list = Allocation.objects.filter(
            resources__name="Storage2",
            start_date__lte=begin_billing,
            end_date__gte=end_billing,
        )

        billing_cycle_sub_query = AllocationAttribute.objects.filter(
            allocation=OuterRef("pk"),
            allocation_attribute_type__name="billing_cycle",
        ).values("value")
        cost_center_sub_query = AllocationAttribute.objects.filter(
            allocation=OuterRef("pk"), allocation_attribute_type__name="cost_center"
        ).values("value")
        subsidized_sub_query = AllocationAttribute.objects.filter(
            allocation=OuterRef("pk"), allocation_attribute_type__name="subsidized"
        ).values("value")
        billing_exempt_sub_query = AllocationAttribute.objects.filter(
            allocation=OuterRef("pk"), allocation_attribute_type__name="billing_exempt"
        ).values("value")
        pi_sub_query = Project.objects.filter(allocation__in=allocation_list).values(
            "pi__username"
        )
        usages_sub_query = AllocationAttributeUsage.history.filter(
            allocation_attribute__allocation__in=allocation_list,
            allocation_attribute__allocation_attribute_type__name="storage_quota",
            history_date__date=end_billing,
        ).values("value")

        allocation_list = allocation_list.annotate(
            billing_cycle=Subquery(billing_cycle_sub_query),
            cost_center=Subquery(cost_center_sub_query),
            billing_exempt=Subquery(billing_exempt_sub_query),
            subsidized=Subquery(subsidized_sub_query),
            pi=Subquery(pi_sub_query),
            usage=Subquery(usages_sub_query),
        ).values(
            "billing_cycle",
            "cost_center",
            "subsidized",
            "billing_exempt",
            "usage",
            "pi",
        )

        return list(allocation_list)
