from allauth.account.urls import urlpatterns as all_patterns

"""Include a subset of patterns from allauth.account."""


urlpatterns = []
names_to_include = {
    'account_inactive',
    'account_email',
    'account_email_verification_sent',
    'account_confirm_email',
}
for pattern in all_patterns:
    if pattern.name in names_to_include:
        urlpatterns.append(pattern)
