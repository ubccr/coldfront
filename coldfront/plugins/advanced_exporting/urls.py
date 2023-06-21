from django.urls import path

from coldfront.plugins.advanced_exporting.views import AdvancedExportingView, AdvancedExportView

urlpatterns = [
    path('advanced-exporting/', AdvancedExportingView.as_view(), name='advanced-exporting'),
    path('export/', AdvancedExportView.as_view(), name='export')
]
