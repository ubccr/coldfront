from coldfront.api.user.views import ObtainActiveUserExpiringAuthToken
from django.conf.urls import url


urlpatterns = [
    url(
        r'^api_token_auth/', ObtainActiveUserExpiringAuthToken.as_view(),
        name='api_token_auth'),
]
