# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""utility functions for unit and integration testing"""


def login_and_get_page(client, user, page):
    """force login and return get response for page"""
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    return client.get(page)


def page_contains_for_user(test_case, user, url, text):
    """Check that page contains text for user"""
    response = login_and_get_page(test_case.client, user, url)
    test_case.assertContains(response, text)


def page_does_not_contain_for_user(test_case, user, url, text):
    """Check that page contains text for user"""
    response = login_and_get_page(test_case.client, user, url)
    test_case.assertNotContains(response, text)


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
    test_case.assertRedirects(response, f"/user/login?next={page}")


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


def test_user_cannot_access(test_case, user, page):
    """Confirm that accessing the page as the designated user returns a 403 response code.

    Parameters
    ----------
    test_case : django.test.TestCase.
        must have "client" attr set.
    user : user object
    page : str
        must begin and end with a slash.
    """
    response = login_and_get_page(test_case.client, user, page)
    test_case.assertEqual(response.status_code, 403)


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
