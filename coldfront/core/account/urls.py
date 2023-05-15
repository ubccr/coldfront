from allauth.account.urls import urlpatterns as all_patterns

from flags.urls import flagged_paths

"""Include a subset of patterns from allauth.account."""


urlpatterns = []


names_to_include = {
    'account_inactive',
    'account_email_verification_sent',
    'account_confirm_email',
}
for pattern in all_patterns:
    if pattern.name in names_to_include:
        urlpatterns.append(pattern)


# Only include the view for managing emails if users are allowed to have
# multiple emails.
names_to_include_if_multiple_emails_allowed = {
    'account_email',
}
with flagged_paths('MULTIPLE_EMAIL_ADDRESSES_ALLOWED') as f_path:
    for pattern in all_patterns:
        if pattern.name in names_to_include_if_multiple_emails_allowed:
            urlpatterns.append(
                f_path(
                    str(pattern.pattern), pattern.callback,
                    pattern.default_args, pattern.name))
