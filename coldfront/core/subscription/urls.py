from django.urls import path

import coldfront.core.subscription.views as subscription_views

urlpatterns = [
    path('', subscription_views.SubscriptionListView.as_view(), name='subscription-list'),
    path('project/<int:project_pk>/create', subscription_views.SubscriptionCreateView.as_view(), name='subscription-create'),
    path('<int:pk>/', subscription_views.SubscriptionDetailView.as_view(), name='subscription-detail'),
    path('<int:pk>/activate-request', subscription_views.SubscriptionActivateRequestView.as_view(),
         name='subscription-activate-request'),
    path('<int:pk>/deny-request', subscription_views.SubscriptionDenyRequestView.as_view(), name='subscription-deny-request'),
    path('<int:pk>/add-users', subscription_views.SubscriptionAddUsersView.as_view(), name='subscription-add-users'),
    path('<int:pk>/remove-users', subscription_views.SubscriptionRemoveUsersView.as_view(), name='subscription-remove-users'),
    path('request-list', subscription_views.SubscriptionRequestListView.as_view(),
         name='subscription-request-list'),
    path('<int:pk>/renew', subscription_views.SubscriptionRenewView.as_view(), name='subscription-renew'),
    path('<int:pk>/subscriptionattribute/add', subscription_views.SubscriptionAttributeCreateView.as_view(), name='subscription-attribute-add'),
    path('<int:pk>/subscriptionattribute/delete', subscription_views.SubscriptionAttributeDeleteView.as_view(), name='subscription-attribute-delete'),
    path('subscription-invoice-list', subscription_views.SubscriptionInvoiceListView.as_view(),
         name='subscription-invoice-list'),
    path('<int:pk>/invoice/', subscription_views.SubscriptionInvoiceDetailView.as_view(), name='subscription-invoice-detail'),
    path('subscription/<int:pk>/add-invoice-note', subscription_views.SubscriptionAddInvoiceNoteView.as_view(), name='subscription-add-invoice-note'),
    path('subscription-invoice-note/<int:pk>/update', subscription_views.SubscriptionUpdateInvoiceNoteView.as_view(), name='subscription-update-invoice-note'),
    path('subscription/<int:pk>/invoice/delete/', subscription_views.SubscriptionDeleteInvoiceNoteView.as_view(), name='subscription-delete-invoice-note'),
    path('add-subscription-account/', subscription_views.SubscriptionAccountCreateView.as_view(), name='add-subscription-account'),
    path('subscription-account-list/', subscription_views.SubscriptionAccountListView.as_view(), name='subscription-account-list'),
]
