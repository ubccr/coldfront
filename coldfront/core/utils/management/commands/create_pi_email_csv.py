import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from coldfront.core.allocation.models import Allocation
base_dir = settings.BASE_DIR

class Command(BaseCommand):

    def handle(self, *args, **options):
        active_allocations = Allocation.objects.filter(
                project__status__name__in=['Active', 'New'],
                status__name__in=['Active', 'New', 'Updated', 'Ready for Review']
                )
        allocation_vals = [{
                "pi_fullname": a.project.pi.full_name,
                "email": a.project.pi.email,
                "project_name": a.project.title,
                "resource": a.resources.first().name,
                "size": a.size,
                "usage": round(a.usage, 2)
            } for a in active_allocations]
        df = pd.DataFrame(allocation_vals)
        print(df)
        df.to_csv('local_data/pi_email_list.csv', index=False)
