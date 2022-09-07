"""Functions for testing the same basic principle across different applications"""
from django.test import Client


### Functions for in-situ error checks from command line ###
def login_return_client(username, password):
    """return a logged-in client object"""
    client = Client()
    client.login(username=username, password=password)
    return client

def collect_all_ids_in_listpage(client, listpage):
    """collect all the ids displayed in the template of a given list view."""
    response = client.get(listpage)
    num_pages = response.context_data['paginator'].num_pages
    obj_ids = [o.id for o in response.context_data['object_list']]
    if num_pages > 1:
        pages = range(2, num_pages)
        for page in pages:
            response = client.get(f"{listpage}&page={page}")
            obj_ids.extend([o.id for o in response.context_data['object_list']])
    return obj_ids

def confirm_loads(client, obj_ids, page_url):
    """Confirm that all pages linked to on a given list page return a 200 status
    code when accessed.

    Parameters
    ----------
    client : django.test Client object. Must be logged in.
    listpage : url string of the page from which to collect information
        structure should be something like '/project/?show_all_projects=on'. No
        '/' character at the end.
    """
    for obj_id in obj_ids:
        url = f"{page_url}{obj_id}/"
        try:
            response = client.get(url)
            # if response.status_code != 200:
            #     print(f"status_code: {response.status_code} url: {url}")
        except Exception as e:
            print(f"ERROR FOR url: {url}   {e}\n{e.__traceback__}")


### Functions for testing library ###
def login_and_get_page(client, user, page):
    """force login and return get response for page"""
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    return client.get(page)

def test_redirect_to_login(test_case, page):
    """
    Confirm that attempting to access page while not logged in triggers a 302
    redirect to a login page.

    Parameters
    ----------
    test_case : must have client.
    page : str
        must begin and end with a slash.
    """
    # log out, in case already logged in
    test_case.client.logout()
    response = test_case.client.get(page)
    test_case.assertEqual(response.status_code, 302)
    test_case.assertEqual(response.url, f"/user/login?next={page}")



def test_user_can_access(test_case, user, page):
    """Confirm that accessing the page as the designated user returns a 200 response code.

    Parameters
    ----------
    test_case : django.test.TestCase.
        must have "client" attr set.
    user : user object
    page : str
        must begin and end with a slash.
    """
    response = login_and_get_page(test_case.client, user, page)
    test_case.assertEqual(response.status_code, 200)
