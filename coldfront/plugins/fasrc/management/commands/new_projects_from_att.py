import logging

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from coldfront.plugins.fasrc.utils import create_new_projects


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    '''
    Create new projects from local_data/ready_to_add/missing_projects.csv.
    The CSV must have a column labeled 'title' which contains the names of the
    AD groups for which equivalent projects will be created in Coldfront.
    '''



    def handle(self, *args, **kwargs):
        project_csv = 'local_data/ready_to_add/missing_projects.csv'
        projects_list = pd.read_csv(project_csv, usecols=['title'])
        create_new_projects(projects_list.title.to_list())
