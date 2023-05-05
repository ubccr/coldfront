from allauth.socialaccount.urls import urlpatterns as all_patterns

from flags.urls import flagged_paths

"""Include a subset of patterns from allauth.socialaccount."""


urlpatterns = []


names_to_include = {
    'socialaccount_login_cancelled',
}
for pattern in all_patterns:
    if pattern.name in names_to_include:
        urlpatterns.append(pattern)


# Only include view for connecting additional social accounts if users are
# allowed to have multiple emails.
names_to_include_if_multiple_emails_allowed = {
    'socialaccount_connections',
}
with flagged_paths('MULTIPLE_EMAIL_ADDRESSES_ALLOWED') as f_path:
    for pattern in all_patterns:
        if pattern.name in names_to_include_if_multiple_emails_allowed:
            urlpatterns.append(
                f_path(
                    pattern.pattern, pattern.callback, pattern.default_args,
                    pattern.name))
