import requests
import oracledb
import logging

from coldfront.core.utils.common import import_from_settings
from coldfront.core.publication.models import Publication, PublicationSource

logger = logging.getLogger(__name__)

ACADEMIC_ANALYTICS_API_KEY = import_from_settings('ACADEMIC_ANALYTICS_API_KEY')
ACADEMIC_ANALYTICS_API_BASE_ADDRESS = import_from_settings('ACADEMIC_ANALYTICS_API_BASE_ADDRESS')
ACADEMIC_ANALYTICS_FORMULA = import_from_settings('ACADEMIC_ANALYTICS_FORMULA')
ORACLE_DB_USER = import_from_settings('ORACLE_DB_USER')
ORACLE_DB_PASSWORD = import_from_settings('ORACLE_DB_PASSWORD')
ORACLE_DB_DSN = import_from_settings('ORACLE_DB_DSN')
ORACLE_DB_QUERY = import_from_settings('ORACLE_DB_QUERY')


def get_user_id(username):
    """
    Connects to an oracle database to grab a users ID.
    """
    user_id = ''
    oracledb.init_oracle_client()
    with oracledb.connect(user=ORACLE_DB_USER, password=ORACLE_DB_PASSWORD, dsn=ORACLE_DB_DSN) as connection:
        with connection.cursor() as cursor:
            user_id = cursor.execute(ORACLE_DB_QUERY.format(username)).fetchall()[0][0]

    return user_id

def format_author(author):
    """
    Reformats the authors to "firstname lastname and firstname lastname and ..."
    """
    if not author:
        return ''

    formatted_authors = []
    authors_split = author.split('|')
    for author in authors_split:
        author_split = author.split(',')
        formatted_author = f'{author_split[1].strip()} {author_split[0].strip()}'
        formatted_authors.append(formatted_author)

    return ' and '.join(formatted_authors)

def format_journal(journal):
    """
    Removes the extra section [######] from the journal's title. 
    """
    if not journal:
        return ''
    
    return journal.split('[')[0].strip()

def get_publications(username):
    """
    Finds all publications a user has within the academic analytics database.
    """
    user_id = get_user_id(username)

    headers = {
        'apikey': ACADEMIC_ANALYTICS_API_KEY
    }

    client_faculty_id = eval(ACADEMIC_ANALYTICS_FORMULA.format(int(user_id)), {'__builtins__':{}}, {})
    person_results = requests.get(
        url=ACADEMIC_ANALYTICS_API_BASE_ADDRESS + f'GetPersonIdByClientFacultyId?clientFacultyId={client_faculty_id}',
        headers=headers
    )
    person_id = person_results.json().get('PersonId')
    if not person_id:
        return []
    
    publications = []
    articles_result = requests.get(
        url=ACADEMIC_ANALYTICS_API_BASE_ADDRESS + f'{person_id}/articles',
        headers=headers
    )
    for articles in articles_result.json():
        publications.append({
            'title': articles.get('ArticleTitle'),
            'author': format_author(articles.get('Authors')),
            'year': articles.get('ArticleYear'),
            'journal': format_journal(articles.get('JournalName')),
            'unique_id': articles.get('DOI'),
        })
    proceedings_result = requests.get(
        url=ACADEMIC_ANALYTICS_API_BASE_ADDRESS + f'{person_id}/proceedings',
        headers=headers
    )
    for proceeding in proceedings_result.json():
        publications.append({
            'title': proceeding.get('ProceedingTitle'),
            'author': format_author(proceeding.get('Authors')),
            'year': proceeding.get('ArticleYear'),
            'journal': format_journal(proceeding.get('JournalName')),
            'unique_id': proceeding.get('DOI'),
        })

    return publications

def remove_existing_publications(project_obj, publications):
    """
    Removes publications from the list that already exist.
    """
    filtered_publications = []
    existing_unique_ids = project_obj.publication_set.filter().values_list('unique_id', flat=True)
    for publication in publications:
        if not publication.get('unique_id') in existing_unique_ids:
            filtered_publications.append(publication)

    return filtered_publications


def add_publication(project_obj, publication):
    """
    Creates a new publication for the provided project.
    """
    source_obj, _ = PublicationSource.objects.get_or_create(
        name='aa'
    )

    publication_obj = Publication.objects.create(
        project=project_obj,
        title=publication.get('title'),
        author=publication.get('author'),
        year=publication.get('year'),
        journal=publication.get('journal'),
        unique_id=publication.get('unique_id'),
        source=source_obj 
    )
    logger.info(
        f'A new publication was added during a project review (publication pk={publication_obj.pk})'
    )