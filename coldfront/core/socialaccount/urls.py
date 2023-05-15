from allauth.socialaccount.urls import urlpatterns as all_patterns

from flags.urls import flagged_paths

"""Include a subset of patterns from allauth.socialaccount."""


urlpatterns = []


# TODO: Come up with a more elegant solution for dealing with views protected by
#  multiple flags.
with flagged_paths('SSO_ENABLED') as sso_f_path:
    names_to_include = {
        'socialaccount_login_cancelled',
    }
    for pattern in all_patterns:
        if pattern.name in names_to_include:
            urlpatterns.append(sso_f_path(
                str(pattern.pattern), pattern.callback,
                pattern.default_args, pattern.name)
            )

    # Only include the view for connecting additional social accounts if users
    # are allowed to have multiple emails.
    names_to_include_if_multiple_emails_allowed = {
        'socialaccount_connections',
    }
    with flagged_paths('MULTIPLE_EMAIL_ADDRESSES_ALLOWED') as multi_email_f_path:
        for pattern in all_patterns:
            if pattern.name in names_to_include_if_multiple_emails_allowed:
                # The URL is not correctly disabled unless passed through both
                # context managers.
                tmp_pattern = multi_email_f_path(
                    str(pattern.pattern), pattern.callback,
                    pattern.default_args, pattern.name)
                final_pattern = sso_f_path(
                    str(tmp_pattern.pattern), tmp_pattern.callback,
                    tmp_pattern.default_args, tmp_pattern.name)
                urlpatterns.append(final_pattern)
