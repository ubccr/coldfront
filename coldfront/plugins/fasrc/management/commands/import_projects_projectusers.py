import logging
from datetime import datetime

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from coldfront.plugins.fasrc.utils import create_new_projects


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    '''
    Create new projects from local_data/ready_to_add/add_projects.csv.
    The CSV must have a column labeled 'title' which contains the names of the
    AD groups for which equivalent projects will be created in Coldfront.
    '''


    def handle(self, *args, **kwargs):
        project_csv = 'local_data/ready_to_add/add_projects.csv'
        projects_list = pd.read_csv(project_csv)
        added_projects, errortracker = create_new_projects(projects_list.title.to_list())
        add_later = errortracker['no_pi'] + errortracker['no_members'] + errortracker['no_managers']
        projects_to_add = projects_list.loc[projects_list['title'].isin(add_later)]
        try:
            projects_to_add['first_attempt'] = projects_to_add['first_attempt'].fillna(datetime.now())
        except KeyError:
            projects_to_add['first_attempt'] = datetime.now()
        projects_to_add['last_attempt'] = datetime.now()
        projects_to_add.to_csv('local_data/ready_to_add/add_projects.csv', index=False)
