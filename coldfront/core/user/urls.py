from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.views import PasswordResetCompleteView
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.views import PasswordResetDoneView
from django.contrib.auth.views import PasswordResetView
from django.urls import path, reverse_lazy

import coldfront.core.user.views as user_views
import coldfront.core.user.views_.request_hub_views as request_hub_views
from coldfront.core.user.forms import VerifiedEmailAddressPasswordResetForm
from coldfront.core.user.forms import UserLoginForm

EXTRA_APPS = settings.EXTRA_APPS


urlpatterns = [
    path('login',
         LoginView.as_view(
             template_name='user/login.html',
             form_class=UserLoginForm,
             extra_context={'EXTRA_APPS': EXTRA_APPS},
             redirect_authenticated_user=True),
         name='login'
         ),
    path('logout',
         LogoutView.as_view(next_page=reverse_lazy('login')),
         name='logout'
         ),
    path('user-access-agreement',
         user_views.user_access_agreement,
         name='user-access-agreement'),
    path('user-profile/', user_views.UserProfile.as_view(), name='user-profile'),
    path('user-profile/<str:viewed_username>', user_views.UserProfile.as_view(), name='user-profile'),
    path('user-profile-update/', user_views.UserProfileUpdate.as_view(), name='user-profile-update'),
    path('user-projects-managers/', user_views.UserProjectsManagersView.as_view(), name='user-projects-managers'),
    path('user-projects-managers/<str:viewed_username>', user_views.UserProjectsManagersView.as_view(), name='user-projects-managers'),
    # path('user-upgrade/', user_views.UserUpgradeAccount.as_view(), name='user-upgrade'),
    path('user-search-home/', user_views.UserSearchHome.as_view(), name='user-search-home'),
    path('user-search-results/', user_views.UserSearchResults.as_view(), name='user-search-results'),
    path('user-list-allocations/', user_views.UserListAllocations.as_view(), name='user-list-allocations'),
    path('user-search-all', user_views.UserSearchAll.as_view(), name='user-search-all'),

    # Password management views
    path('password-change/', user_views.CustomPasswordChangeView.as_view(), name='password-change'),
    path('password-reset/',
         PasswordResetView.as_view(
             form_class=VerifiedEmailAddressPasswordResetForm,
             template_name='user/passwords/password_reset_form.html',
             email_template_name='user/passwords/password_reset_email.html',
             subject_template_name='user/passwords/password_reset_subject.txt',
             success_url=reverse_lazy('password-reset-done')),
         name='password-reset'
         ),
    path('password-reset-done/',
         PasswordResetDoneView.as_view(
             template_name='user/passwords/password_reset_done.html'),
         name='password-reset-done'
         ),
    path('password-reset-confirm/<uidb64>/<token>/',
         PasswordResetConfirmView.as_view(
             template_name='user/passwords/password_reset_confirm.html',
             success_url=reverse_lazy('password-reset-complete')),
         name='password-reset-confirm'
         ),
    path('password-reset-complete/',
         PasswordResetCompleteView.as_view(
             template_name='user/passwords/password_reset_complete.html'),
         name='password-reset-complete'
         ),

    # Registration and activation views
    path('register/',
         user_views.UserRegistrationView.as_view(
             template_name='user/registration.html'),
         name='register'
         ),
    path('activate/<uidb64>/<token>/',
         user_views.activate_user_account,
         name='activate',
         ),
    path('reactivate/',
         user_views.UserReactivateView.as_view(),
         name='reactivate'),

    # Email views
    path('add-email-address',
         user_views.EmailAddressAddView.as_view(),
         name='add-email-address'
         ),
    path('verify-email-address/<uidb64>/<eaidb64>/<token>/',
         user_views.verify_email_address,
         name='verify-email-address'
         ),
    path('send-email-verification-email/<int:pk>',
         user_views.SendEmailAddressVerificationEmailView.as_view(),
         name='send-email-verification-email'
         ),
    path('remove-email-address/<int:pk>',
         user_views.RemoveEmailAddressView.as_view(),
         name='remove-email-address'),
    path('update-primary-email-address',
         user_views.UpdatePrimaryEmailAddressView.as_view(),
         name='update-primary-email-address'),
    path('email-address-exists/<str:email>',
         user_views.EmailAddressExistsView.as_view(),
         name='email-address-exists'),

    path('user-name-exists',
         user_views.UserNameExistsView.as_view(),
         name='user-name-exists'),

    # Link Personal Account
    path('identity-linking-request',
         user_views.IdentityLinkingRequestView.as_view(),
         name='identity-linking-request'),

    # Request Hub
    path('request-hub',
         request_hub_views.RequestHubView.as_view(show_all_requests=False),
         name='request-hub'),

    path('request-hub-admin',
         request_hub_views.RequestHubView.as_view(show_all_requests=True),
         name='request-hub-admin'),
]
