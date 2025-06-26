import requests
import oracledb
import logging

from coldfront.core.utils.common import import_from_settings
from coldfront.core.publication.models import Publication, PublicationSource

ACADEMIC_ANALYTICS_API_KEY = import_from_settings('ACADEMIC_ANALYTICS_API_KEY')
ACADEMIC_ANALYTICS_API_BASE_ADDRESS = import_from_settings('ACADEMIC_ANALYTICS_API_BASE_ADDRESS')
ACADEMIC_ANALYTICS_FORMULA = import_from_settings('ACADEMIC_ANALYTICS_FORMULA')
ORACLE_DB_USER = import_from_settings('ORACLE_DB_USER')
ORACLE_DB_PASSWORD = import_from_settings('ORACLE_DB_PASSWORD')
ORACLE_DB_DSN = import_from_settings('ORACLE_DB_DSN')
ORACLE_DB_QUERY = import_from_settings('ORACLE_DB_QUERY')

logger = logging.getLogger(__name__)


def get_user_ids(usernames):
    """
    Connects to an oracle database to grab users' IDs.
    """
    user_ids = []
    oracledb.init_oracle_client()
    with oracledb.connect(user=ORACLE_DB_USER, password=ORACLE_DB_PASSWORD, dsn=ORACLE_DB_DSN) as connection:
        with connection.cursor() as cursor:
            results = cursor.execute(ORACLE_DB_QUERY.format("'" + "','".join(usernames) + "'")).fetchall()
            user_ids = [user_id[0] for user_id in results]

    return user_ids

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
        try:
            if len(author_split) == 1:
                formatted_author = author
            else:
                formatted_author = f'{author_split[1].strip()} {author_split[0].strip()}'
        except IndexError:
            logger.error(f"Error finding aa author with username: {author}")

        formatted_authors.append(formatted_author)

    return ' and '.join(formatted_authors)

def format_journal(journal):
    """
    Removes the extra section [######] from the journal's title. 
    """
    if not journal:
        return ''
    
    return journal.split('[')[0].strip()

def get_publications(usernames):
    """
    Finds all publications a list of usernames have within the academic analytics database.
    """
    user_ids = get_user_ids(usernames)

    headers = {
        'apikey': ACADEMIC_ANALYTICS_API_KEY
    }

    publications = []
    for user_id in user_ids:
        client_faculty_id = eval(ACADEMIC_ANALYTICS_FORMULA.format(int(user_id)), {'__builtins__':{}}, {})
        person_results = requests.get(
            url=ACADEMIC_ANALYTICS_API_BASE_ADDRESS + f'GetPersonIdByClientFacultyId?clientFacultyId={client_faculty_id}',
            headers=headers
        )
        person_id = person_results.json().get('PersonId')
        if not person_id:
            continue
        
        articles_result = requests.get(
            url=ACADEMIC_ANALYTICS_API_BASE_ADDRESS + f'{person_id}/articles',
            headers=headers
        )
        for article in articles_result.json():
            duplicate = False
            for publication in publications:
                if article.get('DOI') == publication.get('unique_id'):
                    duplicate = True
                    break

            if not duplicate:
                publications.append({
                    'title': article.get('ArticleTitle'),
                    'author': format_author(article.get('Authors')),
                    'year': article.get('ArticleYear'),
                    'journal': format_journal(article.get('JournalName')),
                    'unique_id': article.get('DOI'),
                })
        proceedings_result = requests.get(
            url=ACADEMIC_ANALYTICS_API_BASE_ADDRESS + f'{person_id}/proceedings',
            headers=headers
        )
        for proceeding in proceedings_result.json():
            duplicate = False
            for publication in publications:
                if proceeding.get('DOI') == publication.get('unique_id'):
                    duplicate = True
                    break

            if not duplicate:
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
        if publication.get('unique_id') not in existing_unique_ids:
            filtered_publications.append(publication)

    return filtered_publications


def add_publication(project_obj, publication):
    """
    Creates a new publication for the provided project.
    """
    Publication.objects.create(
        project=project_obj,
        title=publication.get('title'),
        author=publication.get('author')[:1024],
        year=publication.get('year'),
        journal=publication.get('journal'),
        unique_id=publication.get('unique_id'),
        source=PublicationSource.objects.get(name='aa') 
    )
