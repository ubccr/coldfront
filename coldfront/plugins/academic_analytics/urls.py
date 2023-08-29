from django.urls import path

from coldfront.plugins.academic_analytics.views import AcademicAnalyticsPublications

urlpatterns = [
    path('get-publications/', AcademicAnalyticsPublications.as_view(), name='get-academic-analytics-publications'),
]
