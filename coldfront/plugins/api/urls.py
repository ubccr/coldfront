from django.urls import include, path
from rest_framework import routers
from coldfront.plugins.api import views

router = routers.DefaultRouter()
router.register(r'allocation', views.AllocationViewSet, basename='allocation')
router.register(r'resource', views.ResourceViewSet, basename='resource')

urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
