import requests

from django.conf import settings
from coldfront.core.utils.common import import_from_settings

ACADEMIC_ANALYTICS_API_KEY = import_from_settings('ACADEMIC_ANALYTICS_API_KEY', '')
ACADEMIC_ANALYTICS_API_BASE_ADDRESS = import_from_settings('ACADEMIC_ANALYTICS_API_BASE_ADDRESS', '')

def get_client_faculty_id(username):
    pass
    

def get_person_id(client_faculty_id):
    url = None
    headers = {
        'apikey': ACADEMIC_ANALYTICS_API_KEY
    }
    result = requests.get(
        url=url,
        headers=headers
    )

    person_id = result.json().get('PersonId')
    return person_id


def get_publications(username):
    academic_analytics_url = ACADEMIC_ANALYTICS_API_BASE_ADDRESS +'person/list'
    headers = {
        'apikey': ACADEMIC_ANALYTICS_API_KEY
    }
    result = requests.get(
        url=academic_analytics_url,
        headers=headers
    )

    if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
        from coldfront.plugins.ldap_user_info.utils import get_user_info
        username =  username
        attributes = get_user_info(username, ['displayName'])

    person_id = None
    for entry in result.json():
        if attributes['displayName'][0].upper() in entry['PersonName']:
            person_id = entry['PersonId']

    if person_id is not None:
        articles_result = requests.get(
            url=ACADEMIC_ANALYTICS_API_BASE_ADDRESS + f'person/{person_id}/articles',
            headers=headers
        )

    print(articles_result.json())