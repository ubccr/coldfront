from coldfront.api.project.views import ProjectViewSet, \
    ProjectUserRemovalRequestViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='projects')
router.register(r'project_user_removal_requests',
                ProjectUserRemovalRequestViewSet,
                basename='project_user_removal_requests')
urlpatterns = router.urls
