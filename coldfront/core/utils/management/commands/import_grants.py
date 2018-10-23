import datetime
import os
import pprint

import pytz
from django.conf import settings
from django.core.management.base import BaseCommand

from coldfront.core.grant.models import (Grant, GrantFundingAgency,
                                          GrantStatusChoice)
from coldfront.core.project.models import Project

base_dir = settings.BASE_DIR


def get_role_and_pi_mapping():
    delimiter = '$'
    file_path = os.path.join(base_dir, 'local_data', 'grants_role_pi.tsv')

    mapping = {}
    with open(file_path, 'r') as fp:
        for line in fp:
            if line.startswith('#'):
                continue

            PROJECT_TITLE, GRANT_TITLE, RF_Award_Number, ROLE, PI = line.strip().split(delimiter)

            if ROLE == 'coPI':
                ROLE = 'CoPI'

            unique_key = PROJECT_TITLE + GRANT_TITLE
            mapping[unique_key] = {
                'role': ROLE,
                'pi': PI,
                'rf_award_number': RF_Award_Number
            }
    return mapping


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding grants ...')
        Grant.objects.all().delete()

        delimiter = '\t'
        file_path = os.path.join(base_dir, 'local_data', 'grants.tsv')

        agency_mapping = {
            'AHA': 'Other',
            'Army Research Laboratory, MURI': 'Other',
            'Canadian Institutes of Health Research (CIHR)': 'Other',
            'Department of Energy': 'Department of Energy (DOE)',
            'Department of Homeland Security': 'Other',
            'DOE': 'Department of Energy (DOE)',
            'Federal Rail Administration (FRA)': 'Other',
            'Google Inc': 'Other',
            'Hologic Inc.': 'Other',
            'Internal - UB OVPRED (Grant Resubmission Award)': 'Other',
            'NASA': 'National Aeronautics and Space Administration (NASA)',
            'National Institute on Drug Abuse (NIDA)': 'National Institutes of Health (NIH)',
            'National Institutes of Health': 'National Institutes of Health (NIH)',
            'National Nuclear Security Administration': 'Other',
            'National Science Foundation': 'National Science Foundation (NSF)',
            'Navy STTR': 'Other',
            'New York State Center of Excellence in Materials Informatics': 'Other',
            'New York State NYSTAR': "Empire State Development's Division of Science, Technology and Innovation (NYSTAR)",
            'NHLBI': 'National Institutes of Health (NIH)',
            'NIH': 'National Institutes of Health (NIH)',
            'NIH / NLM': 'National Institutes of Health (NIH)',
            'NIH NCATS': 'National Institutes of Health (NIH)',
            'NIH-NHLBI': 'National Institutes of Health (NIH)',
            'NIH/NHLBI': 'National Institutes of Health (NIH)',
            'NOAA': 'Other',
            'Nomura Foundation': 'Other',
            'NSF': 'National Science Foundation (NSF)',
            'nsf': 'National Science Foundation (NSF)',
            'NSF CBET Energy for Sustainability Program': 'National Science Foundation (NSF)',
            'NSF:CIF': 'National Science Foundation (NSF)',
            'NVIDIA': 'Other',
            'NY State Department of Health': 'New York State Department of Health (DOH)',
            'NYS Department of Economic Development': 'New York State (NYS)',
            'NYSTAR through RPI': 'Other',
            'NYSTEM': 'Other',
            'Office of Naval Research': 'Other',
            'RENEW (UB)': 'Other',
            'RENEW Institute - University at Buffalo': 'Other',
            'SUNY': 'Other',
            'UB RENEW': 'Other',
            'UB STEM Mentored Undergraduate Research Initiative': 'Other',
            'UBCAT': 'Other',
            'University at Buffalo CAS and OVPRED': 'Other',
            'US Army Research Office': 'Other',
            'US Department of Energy/NETL': 'Other',
            'VA': 'Other',
            'Wisconsin Highway Research Program': 'Other',
            'Funded by UB through funds for the Samuel P. Capen Professor': 'Other',
            'Arthritis Foundation': 'Other',
            'HRI-Roswell Park': 'Other',
            'DARPA': 'Other',
            'City of Buffalo / Buffalo Sewer Authority': 'Other',
            'NYS Empire State Development': 'Empire State Development (ESD)',
            'NIAMS': 'National Institutes of Health (NIH)',
        }

        role_pi_mapping = get_role_and_pi_mapping()

        with open(file_path, 'r') as fp:
            for line in fp:
                if line.startswith('#'):
                    continue
                created, modified, project__title, project__pi__username, project_status, project_number, title, funding_agency, project_start, project_end, percent_credit, direct_funding, total_amount_awarded, status = line.strip().split(delimiter)

                created = datetime.datetime.strptime(created.split('.')[0], '%Y-%m-%d %H:%M:%S')
                modified = datetime.datetime.strptime(modified.split('.')[0], '%Y-%m-%d %H:%M:%S')
                project_start = datetime.datetime.strptime(project_start, '%Y-%m-%d')
                project_end = datetime.datetime.strptime(project_end, '%Y-%m-%d')

                if funding_agency in agency_mapping:
                    funding_agency_obj = GrantFundingAgency.objects.get(name=agency_mapping[funding_agency])
                    if agency_mapping[funding_agency] == 'Other':
                        other_funding_agency = funding_agency
                    else:
                        other_funding_agency = ''
                else:
                    funding_agency_obj = GrantFundingAgency.objects.get(name='Other')
                    other_funding_agency = funding_agency

                unique_key = project__title + title
                if unique_key in role_pi_mapping:
                    role = role_pi_mapping[unique_key].get('role')
                    grant_pi_full_name = role_pi_mapping[unique_key].get('pi')
                    rf_award_number = role_pi_mapping[unique_key].get('rf_award_number')
                else:
                    role = 'PI'
                    grant_pi_full_name = ''
                    rf_award_number = 0

                try:
                    project_obj = Project.objects.get(title=project__title.strip(),
                    pi__username=project__pi__username.strip(), status__name=project_status)
                except:
                    print(project__title, project__pi__username)


                grant_status_choice_obj = GrantStatusChoice.objects.get(name=status.title())
                grant_obj, created = Grant.objects.get_or_create(
                    created=created,
                    modified=modified,
                    project=project_obj,
                    grant_number=project_number,
                    title=title,
                    role=role,
                    grant_pi_full_name=grant_pi_full_name,
                    funding_agency=funding_agency_obj,
                    other_funding_agency=other_funding_agency,
                    other_award_number=rf_award_number,
                    grant_start=project_start,
                    grant_end=project_end,
                    percent_credit=percent_credit,
                    direct_funding=direct_funding,
                    total_amount_awarded=total_amount_awarded,
                    status=grant_status_choice_obj
                    )


        print('Finished adding grants.')
