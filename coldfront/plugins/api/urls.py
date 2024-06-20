from django.urls import include, path
from rest_framework import routers
from coldfront.plugins.api import views

router = routers.DefaultRouter()
router.register(r'allocations', views.AllocationViewSet, basename='allocations')
router.register(r'resources', views.ResourceViewSet, basename='resources')
router.register(r'projects', views.ProjectViewSet, basename='projects')
router.register(r'users', views.UserViewSet, basename='users')
router.register(r'allocation-change-requests', views.AllocationChangeRequestViewSet, basename='allocation-change-requests')

urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
