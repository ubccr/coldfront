from coldfront.api.statistics.views import can_submit_job
from coldfront.api.statistics.views import JobViewSet
from coldfront.api.user.views import ObtainActiveUserExpiringAuthToken
from django.conf.urls import url
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='jobs')
urlpatterns = router.urls

urlpatterns.append(url(
    r'^api_token_auth/', ObtainActiveUserExpiringAuthToken.as_view(),
    name='api_token_auth'))

urlpatterns.append(url(
    r'^can_submit_job/(?P<job_cost>.*)/(?P<user_id>.*)/(?P<account_id>.*)/$',
    can_submit_job, name='can_submit_job'))


schema_view = get_schema_view(
    openapi.Info(
        title='myBRC REST API',
        default_version='v1',
        description='REST API for myBRC'),
    public=True,
    permission_classes=(permissions.AllowAny,))

urlpatterns.append(url(
    r'^swagger(?P<format>\.json|\.yaml)$',
    schema_view.without_ui(cache_timeout=0), name='schema-json'))

urlpatterns.append(url(
    r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0),
    name='schema-swagger-ui'))

urlpatterns.append(url(
    r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0),
    name='schema-redoc'))
