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


### Functions for testing library ###
def login_and_get_page(client, user, page):
    """force login and return get response for page"""
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    return client.get(page)

def test_logged_out_redirect_to_login(test_case, page):
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


def test_redirect(test_case, page):
    """
    Confirm that attempting to access page in whatever test_case state is given
    produces a redirect.

    Parameters
    ----------
    test_case : must have client.
    page : str
        must begin and end with a slash.

    Returns
    -------
    response.url : string
        the redirected url given.
    """
    response = test_case.client.get(page)
    test_case.assertEqual(response.status_code, 302)
    return response.url


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
