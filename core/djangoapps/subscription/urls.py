from django.urls import path

import core.djangoapps.subscription.views as subscription_views

urlpatterns = [
    path('', subscription_views.SubscriptionListView.as_view(), name='subscription-list'),
    path('project/<int:project_pk>/create', subscription_views.SubscriptionCreateView.as_view(), name='subscription-create'),
    path('<int:pk>/', subscription_views.SubscriptionDetailView.as_view(), name='subscription-detail'),
    path('<int:pk>/approve-pending-request', subscription_views.SubscriptionApprovePendingRequestView.as_view(),
         name='subscription-approve-request'),
    path('<int:pk>/deny-pending-request', subscription_views.SubscriptionDenyPendingRequestView.as_view(), name='subscription-deny-request'),
    path('<int:pk>/email-pending-request', subscription_views.SubscriptionEmailPendingRequestView.as_view(), name='subscription-email-request'),
    path('<int:pk>/add-users', subscription_views.SubscriptionAddUsersView.as_view(), name='subscription-add-users'),
    path('<int:pk>/delete-users', subscription_views.SubscriptionDeleteUsersView.as_view(), name='subscription-delete-users'),
    path('review-new-requests', subscription_views.SubscriptionReviewPendingRequestsView.as_view(),
         name='subscription-review-pending-requests'),
]
