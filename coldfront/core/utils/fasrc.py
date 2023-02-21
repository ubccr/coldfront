"""A module for fasrc-specific utility functions
"""
import os
import json
import operator
from functools import reduce
from datetime import datetime

import pandas as pd
from ifxbilling.models import Product
from django.db.models import Q
from django.contrib.auth import get_user_model

from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource

MISSING_DATA_DIR = './local_data/missing/'


def select_one_project_allocation(project_obj, resource_obj, dirpath=None):
    '''
    Get one allocation for a given project/resource pairing; handle return of
    zero or multiple allocations.

    If multiple allocations are in allocation_query, choose the one with the
    similar dirpath.

    Parameters
    ----------
    project_obj
    resource_obj
    '''
    allocation_query = project_obj.allocation_set.filter(resources__id=resource_obj.id)
    if allocation_query.count() == 1:
        allocation_obj = allocation_query.first()
    elif allocation_query.count() < 1:
        allocation_obj = None
    elif allocation_query.count() > 1:
        allocation_obj = next((a for a in allocation_query if a.dirpath in dirpath),
                                "MultiAllocationError")
    return allocation_obj


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
    Collect all Resource entries with resources in param resourceserver_list;
    return tuple of all matching Resource entries and all servers with no Resource entries.
    '''
    present_resources = Resource.objects.filter(reduce(operator.or_,
                    (Q(name__contains=x) for x in resourceserver_list)))
    res_names = [str(r.name).split('/')[0] for r in present_resources]
    missing_res = [res for res in resourceserver_list if res not in res_names]
    return (present_resources, missing_res)


def id_present_missing_projects(title_list):
    '''
    Collect all Project entries with titles in param title_list; return tuple
    of all matching Project entries and all titles with no Project entries.
    '''
    present_projects = Project.objects.filter(title__in=title_list)
    proj_titles = [p.title for p in present_projects]
    missing_project_titles = [{"title": title} for title in title_list if title not in proj_titles]
    return (present_projects, missing_project_titles)


def id_present_missing_users(username_list):
    '''
    Collect all User entries with usernames in param username_list; return tuple
    of all matching User entries and all usernames with no User entries.
    '''
    present_users = get_user_model().objects.filter(username__in=username_list)
    present_usernames = [u.username for u in present_users]
    missing_usernames = [{"username": name} for name in username_list if name not in present_usernames]
    return (present_users, missing_usernames)


def log_missing(modelname, missing):
    '''log missing entries for a given Coldfront model.
    Add or update entries in CSV, order CSV by descending date and save.

    Parameters
    ----------
    modelname : string
        lowercase name of the Coldfront model for "missing"
    missing : list of dicts
        identifying information to record for missing entries:
            for users, "username".
            for projects, "title".
            for allocations, "resource_name" and "project_title".
    '''
    if missing:
        locate_or_create_dirpath(MISSING_DATA_DIR)
        fpath = f'{MISSING_DATA_DIR}missing_{modelname}s.csv'
        try:
            missing_df = pd.read_csv(fpath, parse_dates=['date'])
        except FileNotFoundError:
            missing_df = pd.DataFrame()
        new_records = pd.DataFrame(missing)
        col_checks = new_records.columns.values.tolist()
        new_records['date'] = datetime.today()
        missing_df = (pd.concat([missing_df, new_records])
                        .drop_duplicates(col_checks, keep='last')
                        .sort_values('date', ascending=False)
                        .reset_index(drop=True))
        missing_df.to_csv(fpath, index=False)


def locate_or_create_dirpath(dpath):
    if not os.path.exists(dpath):
        os.makedirs(dpath)


def read_json(filepath):
    with open(filepath, 'r') as json_file:
        data = json.loads(json_file.read())
    return data

def save_json(file, contents):
    with open(file, 'w') as fp:
        json.dump(contents, fp, sort_keys=True, indent=4)
