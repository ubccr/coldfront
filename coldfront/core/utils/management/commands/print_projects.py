from django.db.models import Count

from coldfront.core.statistics.models import Job
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create print out projects and pis."

    def handle(self, *args, **options):

        l = Job.objects.values('accountid').\
            order_by('accountid').\
            annotate(num_job=Count('accountid')).\
            order_by('-num_job').\
            values_list('accountid__name', 'num_job')

        total_jobs = sum([x[1] for x in l])
        top_10 = sum(x[1] for x in l[:10])
        top_20 = sum(x[1] for x in l[:20])

        print(total_jobs, top_10, top_10/total_jobs*100, top_20, top_20/total_jobs*100,)
