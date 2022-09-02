"""Functions for testing the same basic principle across different applications"""

def login_and_get_page(client, user, page):
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
