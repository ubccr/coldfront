"""Functions for testing the same basic principle across different applications"""

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


def test_admin_can_access(test_case, page):
    """Confirm that an admin-level user accessing the page returns a 200 response code.

    Parameters
    ----------
    test_case : django.test.TestCase.
        must have client and admin_user attrs.
    page : str
        must begin and end with a slash.
    """
    # admin can access
    test_case.client.force_login(
                            test_case.admin_user,
                            backend="django.contrib.auth.backends.ModelBackend"
                            )
    response = test_case.client.get(page)
    test_case.assertEqual(response.status_code, 200)

def test_user_can_access(test_case, user, page):
    """Confirm that an admin-level user accessing the page returns a 200 response code.

    Parameters
    ----------
    test_case : django.test.TestCase.
        must have client and admin_user attrs.
    page : str
        must begin and end with a slash.
    """
    # admin can access
    test_case.client.force_login(
                            user,
                            backend="django.contrib.auth.backends.ModelBackend"
                            )
    response = test_case.client.get(page)
    test_case.assertEqual(response.status_code, 200)
