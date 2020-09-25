from coldfront.api.statistics.views import can_submit_job
from coldfront.api.statistics.views import JobViewSet
from django.conf.urls import url
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='jobs')
urlpatterns = router.urls

urlpatterns.append(url(
    r'^can_submit_job/(?P<job_cost>.*)/(?P<user_id>.*)/(?P<account_id>.*)/$',
    can_submit_job, name='can_submit_job'))
