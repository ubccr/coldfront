from coldfront.api.allocation.views import AllocationAttributeViewSet
from coldfront.api.allocation.views import AllocationViewSet
from coldfront.api.allocation.views import AllocationUserAttributeViewSet
from coldfront.api.allocation.views import AllocationUserViewSet
from coldfront.api.allocation.views import HistoricalAllocationAttributeViewSet
from coldfront.api.allocation.views import HistoricalAllocationUserAttributeViewSet
from coldfront.api.project.views import ProjectViewSet
from coldfront.api.statistics.views import can_submit_job
from coldfront.api.statistics.views import JobViewSet
from coldfront.api.user.views import ObtainActiveUserExpiringAuthToken
from django.conf.urls import url
from django.urls import include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter


router = DefaultRouter()
router.register(r'accounts', ProjectViewSet, basename='accounts')

router.register(r'allocations', AllocationViewSet, basename='allocations')
allocations_router = NestedSimpleRouter(
    router, r'allocations', lookup='allocation')
allocations_router.register(
    r'attributes', AllocationAttributeViewSet,
    basename='attributes')
allocation_attributes_router = NestedSimpleRouter(
    allocations_router, r'attributes', lookup='attribute')
allocation_attributes_router.register(
    r'history', HistoricalAllocationAttributeViewSet, basename='history')

router.register(
    r'allocation_users', AllocationUserViewSet, basename='allocation_users')
allocation_users_router = NestedSimpleRouter(
    router, r'allocation_users', lookup='allocation_user')
allocation_users_router.register(
    r'attributes', AllocationUserAttributeViewSet, basename='attributes')
allocation_user_attributes_router = NestedSimpleRouter(
    allocation_users_router, r'attributes', lookup='attribute')
allocation_user_attributes_router.register(
    r'history', HistoricalAllocationUserAttributeViewSet, basename='history')

router.register(r'jobs', JobViewSet, basename='jobs')


urlpatterns = router.urls

urlpatterns.append(url('^', include(allocations_router.urls)))
urlpatterns.append(url('^', include(allocation_attributes_router.urls)))

urlpatterns.append(url('^', include(allocation_users_router.urls)))
urlpatterns.append(url('^', include(allocation_user_attributes_router.urls)))


urlpatterns.append(url(
    r'^can_submit_job/(?P<job_cost>.*)/(?P<user_id>.*)/(?P<account_id>.*)/$',
    can_submit_job, name='can_submit_job'))


urlpatterns.append(url(
    r'^api_token_auth/', ObtainActiveUserExpiringAuthToken.as_view(),
    name='api_token_auth'))


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
