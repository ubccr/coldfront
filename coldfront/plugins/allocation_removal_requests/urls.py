from django.urls import path

import coldfront.plugins.allocation_removal_requests.views as views


app_name = 'allocation_removal_requests'
urlpatterns = [
     path('<int:pk>/allocation-removal-request/', views.AllocationRemovalRequestView.as_view(),
         name='allocation-removal-request'),
     path('<int:pk>/allocation-remove/', views.AllocationRemoveView.as_view(),
         name='allocation-remove'),
     path('removal-list/', views.AllocationRemovalListView.as_view(),
         name='allocation-removal-request-list'),
     path('<int:pk>/allocation-approve-removal/', views.AllocationApproveRemovalRequestView.as_view(),
         name='allocation-approve-removal-request'),
     path('<int:pk>/allocation-deny-removal/', views.AllocationDenyRemovalRequestView.as_view(),
         name='allocation-deny-removal-request'),
]
