from django.urls import path
from django.views.generic import TemplateView

from flags.urls import flagged_paths

import coldfront.core.project.views as project_views
import coldfront.core.project.views_.addition_views.approval_views as addition_approval_views
import coldfront.core.project.views_.addition_views.request_views as addition_request_views
import coldfront.core.project.views_.new_project_views.approval_views as new_project_approval_views
import coldfront.core.project.views_.new_project_views.request_views as new_project_request_views
import coldfront.core.project.views_.removal_views as removal_views
import coldfront.core.project.views_.renewal_views.approval_views as renewal_approval_views
import coldfront.core.project.views_.renewal_views.request_views as renewal_request_views


urlpatterns = [
    path('<int:pk>/', project_views.ProjectDetailView.as_view(), name='project-detail'),
    path('<int:pk>/archive', project_views.ProjectArchiveProjectView.as_view(), name='project-archive'),
    path('', project_views.ProjectListView.as_view(), name='project-list'),
    path('project-user-update-email-notification/', project_views.project_update_email_notification, name='project-user-update-email-notification'),
    path('archived/', project_views.ProjectArchivedListView.as_view(), name='project-archived-list'),
    path('create/', project_views.ProjectCreateView.as_view(), name='project-create'),
    path('join/', project_views.ProjectJoinListView.as_view(), name='project-join-list'),
    path('<int:pk>/update/', project_views.ProjectUpdateView.as_view(), name='project-update'),
    path('<int:pk>/add-users-search/', project_views.ProjectAddUsersSearchView.as_view(), name='project-add-users-search'),
    path('<int:pk>/add-users-search-results/', project_views.ProjectAddUsersSearchResultsView.as_view(), name='project-add-users-search-results'),
    path('<int:pk>/add-users/', project_views.ProjectAddUsersView.as_view(), name='project-add-users'),
    path('<int:pk>/user-detail/<int:project_user_pk>', project_views.ProjectUserDetail.as_view(), name='project-user-detail'),
    path('<int:pk>/review/', project_views.ProjectReviewView.as_view(), name='project-review'),
    path('<int:pk>/join/', project_views.ProjectJoinView.as_view(), name='project-join'),
    path('<int:pk>/review-join-requests/', project_views.ProjectReviewJoinRequestsView.as_view(), name='project-review-join-requests'),
    path('project-review-list', project_views.ProjectReviewListView.as_view(),name='project-review-list'),
    path('project-review-complete/<int:project_review_pk>/', project_views.ProjectReviewCompleteView.as_view(),
         name='project-review-complete'),
    path('project-review/<int:pk>/email', project_views.ProjectReivewEmailView.as_view(), name='project-review-email'),
    path('join-list/', project_views.ProjectJoinRequestListView.as_view(), name='project-join-request-list'),
]


# New Project Requests
urlpatterns += [
    path('project-request/',
         new_project_request_views.ProjectRequestView.as_view(),
         name='project-request'),
    path('project-request-landing/',
         new_project_request_views.NewProjectRequestLandingView.as_view(),
         name='project-request-landing'),
    path('new-project-request/',
         new_project_request_views.SavioProjectRequestWizard.as_view(
             condition_dict=new_project_request_views.SavioProjectRequestWizard.condition_dict(),
         ),
         name='new-project-request'),
    path('new-project-pending-request-list/',
         new_project_approval_views.SavioProjectRequestListView.as_view(
             completed=False),
         name='new-project-pending-request-list'),
    path('new-project-completed-request-list/',
         new_project_approval_views.SavioProjectRequestListView.as_view(
             completed=True),
         name='new-project-completed-request-list'),
    path('new-project-request/<int:pk>/',
         new_project_approval_views.SavioProjectRequestDetailView.as_view(),
         name='new-project-request-detail'),
    path('new-project-request/<int:pk>/eligibility/',
         new_project_approval_views.SavioProjectReviewEligibilityView.as_view(),
         name='new-project-request-review-eligibility'),
    path('new-project-request/<int:pk>/readiness/',
         new_project_approval_views.SavioProjectReviewReadinessView.as_view(),
         name='new-project-request-review-readiness'),
    path('new-project-request/<int:pk>/memorandum-signed/',
         new_project_approval_views.SavioProjectReviewMemorandumSignedView.as_view(),
         name='new-project-request-review-memorandum-signed'),
    path('new-project-request/<int:pk>/setup/',
         new_project_approval_views.SavioProjectReviewSetupView.as_view(),
         name='new-project-request-review-setup'),
    path('new-project-request/<int:pk>/deny/',
         new_project_approval_views.SavioProjectReviewDenyView.as_view(),
         name='new-project-request-review-deny'),
    path('new-project-request/<int:pk>/undeny',
         new_project_approval_views.SavioProjectUndenyRequestView.as_view(),
         name='new-project-undeny-request'),
]


# New Project Requests for Vector (BRC-exclusive)
with flagged_paths('BRC_ONLY') as f_path:
    urlpatterns += [
        f_path('project-request-vector-landing/',
               TemplateView.as_view(
                   template_name=(
                       'project/project_request/vector/project_request_landing.html')
               ),
               name='project-request-vector-landing'),
        f_path('vector-project-request/',
               new_project_request_views.VectorProjectRequestView.as_view(),
               name='vector-project-request'),
        f_path('vector-project-pending-request-list/',
               new_project_approval_views.VectorProjectRequestListView.as_view(
                   completed=False),
               name='vector-project-pending-request-list'),
        f_path('vector-project-completed-request-list/',
               new_project_approval_views.VectorProjectRequestListView.as_view(
                   completed=True),
               name='vector-project-completed-request-list'),
        f_path('vector-project-request/<int:pk>/',
               new_project_approval_views.VectorProjectRequestDetailView.as_view(),
               name='vector-project-request-detail'),
        f_path('vector-project-request/<int:pk>/eligibility',
               new_project_approval_views.VectorProjectReviewEligibilityView.as_view(),
               name='vector-project-request-review-eligibility'),
        f_path('vector-project-request/<int:pk>/setup',
               new_project_approval_views.VectorProjectReviewSetupView.as_view(),
               name='vector-project-request-review-setup'),
        f_path('vector-project-request/<int:pk>/undeny',
               new_project_approval_views.VectorProjectUndenyRequestView.as_view(),
               name='vector-project-undeny-request'),
    ]


# ProjectUser Removal Requests
urlpatterns += [
    path('<int:pk>/remove-self',
         removal_views.ProjectRemoveSelf.as_view(),
         name='project-remove-self'),
    path('project-removal-request-list',
         removal_views.ProjectRemovalRequestListView.as_view(completed=False),
         name='project-removal-request-list'),
    path('project-removal-request-list-completed',
         removal_views.ProjectRemovalRequestListView.as_view(completed=True),
         name='project-removal-request-list-completed'),
    path('project-removal-request/<int:pk>/update-status',
         removal_views.ProjectRemovalRequestUpdateStatusView.as_view(),
         name='project-removal-request-update-status'),
    path('project-removal-request/<int:pk>/complete-status',
         removal_views.ProjectRemovalRequestCompleteStatusView.as_view(),
         name='project-removal-request-complete-status'),
    path('<int:pk>/remove-users/',
         removal_views.ProjectRemoveUsersView.as_view(),
         name='project-remove-users'),
]


# Allocation Renewal Requests
urlpatterns += [
    path('<int:pk>/renew',
         renewal_request_views.AllocationRenewalRequestUnderProjectView.as_view(),
         name='project-renew'),
    path('renew-pi-allocation-landing/',
         TemplateView.as_view(
             template_name='project/project_renewal/request_landing.html'),
         name='renew-pi-allocation-landing'),
    path('renew-pi-allocation/',
         renewal_request_views.AllocationRenewalRequestView.as_view(
             condition_dict=renewal_request_views.AllocationRenewalRequestView.condition_dict(),
         ),
         name='renew-pi-allocation'),
    path('pi-allocation-renewal-pending-request-list/',
         renewal_approval_views.AllocationRenewalRequestListView.as_view(
             completed=False),
         name='pi-allocation-renewal-pending-request-list'),
    path('pi-allocation-renewal-completed-request-list/',
         renewal_approval_views.AllocationRenewalRequestListView.as_view(
             completed=True),
         name='pi-allocation-renewal-completed-request-list'),
    path('pi-allocation-renewal-request-detail/<int:pk>/',
         renewal_approval_views.AllocationRenewalRequestDetailView.as_view(),
         name='pi-allocation-renewal-request-detail'),
    path('pi-allocation-renewal-request/<int:pk>/eligibility/',
         renewal_approval_views.AllocationRenewalRequestReviewEligibilityView.as_view(),
         name='pi-allocation-renewal-request-review-eligibility'),
    path('pi-allocation-renewal-request/<int:pk>/deny/',
         renewal_approval_views.AllocationRenewalRequestReviewDenyView.as_view(),
         name='pi-allocation-renewal-request-review-deny'),
    # This is disabled because a PI may always make a new request.
    # path('pi-allocation-renewal-request/<int:pk>/undeny/',
    #      AllocationRenewalRequestUndenyView.as_view(),
    #      name='pi-allocation-renewal-request-review-undeny'),
]


# Purchase Service Units
with flagged_paths('SERVICE_UNITS_PURCHASABLE'):
    urlpatterns += [
        f_path('<int:pk>/purchase-service-units-landing/',
               addition_request_views.AllocationAdditionRequestLandingView.as_view(),
               name='purchase-service-units-landing'),
        f_path('<int:pk>/purchase-service-units/',
               addition_request_views.AllocationAdditionRequestView.as_view(),
               name='purchase-service-units'),
        f_path('service-units-purchase-pending-request-list/',
               addition_approval_views.AllocationAdditionRequestListView.as_view(
                   completed=False),
               name='service-units-purchase-pending-request-list'),
        f_path('service-units-purchase-completed-request-list/',
               addition_approval_views.AllocationAdditionRequestListView.as_view(
                   completed=True),
               name='service-units-purchase-completed-request-list'),
        f_path('service-units-purchase-request/<int:pk>/',
               addition_approval_views.AllocationAdditionRequestDetailView.as_view(),
               name='service-units-purchase-request-detail'),
        f_path('service-units-purchase-request/<int:pk>/memorandum-signed',
               addition_approval_views.AllocationAdditionReviewMemorandumSignedView.as_view(),
               name='service-units-purchase-request-review-memorandum-signed'),
        f_path('service-units-purchase-request/<int:pk>/deny',
               addition_approval_views.AllocationAdditionReviewDenyView.as_view(),
               name='service-units-purchase-request-review-deny'),
    ]
