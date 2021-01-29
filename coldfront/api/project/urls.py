from coldfront.api.project.views import ProjectViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='projects')
urlpatterns = router.urls
