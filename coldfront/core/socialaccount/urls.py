from allauth.socialaccount.urls import urlpatterns as all_patterns

"""Include a subset of patterns from allauth.socialaccount."""


urlpatterns = []
names_to_include = {
    'socialaccount_login_cancelled',
    'socialaccount_connections',
}
for pattern in all_patterns:
    if pattern.name in names_to_include:
        urlpatterns.append(pattern)
