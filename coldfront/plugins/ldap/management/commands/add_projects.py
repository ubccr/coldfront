import logging
from datetime import datetime

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from coldfront.plugins.ldap.utils import import_projects_projectusers


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Create new projects from local_data/ready_to_add/add_projects.csv.
    The CSV must have a column labeled 'title' which contains the names of the
    AD groups for which equivalent projects will be created in Coldfront.
    """


    def handle(self, *args, **kwargs):
        project_csv = 'local_data/ready_to_add/add_projects.csv'
        projects_list = pd.read_csv(project_csv)
        added_projects, errs = import_projects_projectusers(projects_list.title.to_list())
        add_later = errs['no_pi'] + [errs['not_found']] + errs['no_fos']
        projects_to_add = projects_list.loc[projects_list['title'].isin(add_later)].copy()
        try:
            projects_to_add['first_attempt'] = projects_to_add['first_attempt'].fillna(datetime.now())
        except KeyError:
            projects_to_add['first_attempt'] = datetime.now()
        projects_to_add['last_attempt'] = datetime.now()
        projects_to_add.to_csv('local_data/ready_to_add/add_projects.csv', index=False)
