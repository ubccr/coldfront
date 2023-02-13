"""A module for fasrc-specific utility functions
"""

import operator
from functools import reduce
from datetime import datetime

import pandas as pd
from ifxbilling.models import Product
from django.db.models import Q
from django.contrib.auth import get_user_model

from coldfront.core.project.models import Project
from coldfront.core.allocation.models import Allocation
from coldfront.core.resource.models import Resource

MISSING_DATA_DIR = './local_data/missing/'


def determine_size_fmt(byte_num):
    '''Return the correct human-readable byte measurement.
    '''
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]
    for u in units:
        unit = u
        if abs(byte_num) < 1024.0:
            return round(byte_num, 3), unit
        byte_num /= 1024.0
    return(round(byte_num, 3), unit)

def convert_size_fmt(num, target_unit, source_unit="B"):
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]
    diff = units.index(target_unit) - units.index(source_unit)
    if diff == 0:
        pass
    elif diff > 0:
        for i in range(diff):
            num/=1024.0
    elif diff < 0:
        for i in range(abs(diff)):
            num*=1024.0
    return round(num, 3)

def get_resource_rate(resource):
    """find Product with the name provided and return the associated rate"""
    prod_obj = Product.objects.get(product_name=resource)
    rate_obj = prod_obj.rate_set.get(is_active=True)
    # return charge per TB, adjusted to dollar value
    if rate_obj.units == "TB":
        return rate_obj.price/100
    price = convert_size_fmt(rate_obj.price, "TB", source_unit=rate_obj.units)
    return round(price/100, 2)


def id_present_missing_resources(resourceserver_list):
    '''
    '''
    present_resources = Resource.objects.filter(reduce(operator.or_,
                    (Q(name__contains=x) for x in resourceserver_list)))
    res_names = [str(r.name).split('/')[0] for r in present_resources]
    missing_res = [res for res in resourceserver_list if res not in res_names]
    return (present_resources, missing_res)



def id_present_missing_projects(project_title_list):
    '''
    '''
    present_projects = Project.objects.filter(title__in=project_title_list)
    proj_titles = [p.title for p in present_projects]
    missing_project_titles = [title for title in project_title_list if title not in proj_titles]
    return (present_projects, missing_project_titles)


def id_present_missing_users(username_list):
    '''
    Collect all User entries with usernames in param username_list; return tuple
    of all matching User entries and all usernames with no User entries.
    '''
    present_users = get_user_model().objects.filter(username__in=username_list)
    present_usernames = [u.username for u in present_users]
    missing_usernames = [name for name in username_list if name not in present_usernames]
    return (present_users, missing_usernames)


def log_missing(modelname,
                missing,
                group='',
                pattern='I,D'):
    '''

    Parameters
    ----------
    search_list : list of

    '''
    fpath = f'{MISSING_DATA_DIR}missing_{modelname}s.csv'
    datestr = datetime.today().strftime('%Y%m%d')
    patterns = [pattern.replace('I', i).replace('D', datestr).replace('G', group) for i in missing]
    find_or_add_file_line(fpath, patterns)
    return missing


def find_or_add_file_line(filepath, patterns):
    '''Find or add lines matching a string contained in a list to a file.

    Parameters
    ----------
    filepath : string
        path and name of file to check.
    patterns : list
        list of lines to find or append to file.
    '''
    with open(filepath, 'a+') as file:
        file.seek(0)
        lines = file.readlines()
        for pattern in patterns:
            if not any(pattern == line.rstrip('\r\n') for line in lines):
                file.write(pattern + '\n')
