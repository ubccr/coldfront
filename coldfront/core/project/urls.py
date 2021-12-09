from django.urls import path

import coldfront.core.project.views as project_views

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
    # path('<int:pk>/remove-users/', project_views.ProjectRemoveUsersView.as_view(), name='project-remove-users'),
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


# TODO: Once finalized, move these imports above.
from coldfront.core.project.views import ProjectRequestView
from coldfront.core.project.views import SavioProjectRequestDetailView
from coldfront.core.project.views import SavioProjectRequestListView
from coldfront.core.project.views import SavioProjectRequestWizard
from coldfront.core.project.views import SavioProjectReviewAllocationDatesView
from coldfront.core.project.views import SavioProjectReviewDenyView
from coldfront.core.project.views import SavioProjectReviewEligibilityView
from coldfront.core.project.views import SavioProjectReviewMemorandumSignedView
from coldfront.core.project.views import SavioProjectReviewReadinessView
from coldfront.core.project.views import SavioProjectReviewSetupView
from coldfront.core.project.views import SavioProjectUndenyRequestView
from coldfront.core.project.views import show_details_form_condition
from coldfront.core.project.views import show_ica_extra_fields_form_condition
from coldfront.core.project.views import show_new_pi_form_condition
from coldfront.core.project.views import show_pool_allocations_form_condition
from coldfront.core.project.views import show_pooled_project_selection_form_condition
from coldfront.core.project.views import show_recharge_extra_fields_form_condition
from coldfront.core.project.views import VectorProjectRequestDetailView
from coldfront.core.project.views import VectorProjectRequestListView
from coldfront.core.project.views import VectorProjectRequestView
from coldfront.core.project.views import VectorProjectReviewEligibilityView
from coldfront.core.project.views import VectorProjectReviewSetupView
from coldfront.core.project.views import VectorProjectUndenyRequestView
from django.views.generic import TemplateView


urlpatterns += [
    path('project-request/',
         ProjectRequestView.as_view(),
         name='project-request'),
    path('project-request-savio-landing/',
         TemplateView.as_view(
             template_name=(
                 'project/project_request/savio/project_request_landing.html')
         ),
         name='project-request-savio-landing'),
    path('savio-project-request/',
         SavioProjectRequestWizard.as_view(
             condition_dict={
                 '2': show_new_pi_form_condition,
                 '3': show_ica_extra_fields_form_condition,
                 '4': show_recharge_extra_fields_form_condition,
                 '5': show_pool_allocations_form_condition,
                 '6': show_pooled_project_selection_form_condition,
                 '7': show_details_form_condition,
             }
         ),
         name='savio-project-request'),
    path('savio-project-pending-request-list/',
         SavioProjectRequestListView.as_view(completed=False),
         name='savio-project-pending-request-list'),
    path('savio-project-completed-request-list/',
         SavioProjectRequestListView.as_view(completed=True),
         name='savio-project-completed-request-list'),
    path('savio-project-request/<int:pk>/',
         SavioProjectRequestDetailView.as_view(),
         name='savio-project-request-detail'),
    path('savio-project-request/<int:pk>/eligibility/',
         SavioProjectReviewEligibilityView.as_view(),
         name='savio-project-request-review-eligibility'),
    path('savio-project-request/<int:pk>/readiness/',
         SavioProjectReviewReadinessView.as_view(),
         name='savio-project-request-review-readiness'),
    path('savio-project-request/<int:pk>/allocation-dates/',
         SavioProjectReviewAllocationDatesView.as_view(),
         name='savio-project-request-review-allocation-dates'),
    path('savio-project-request/<int:pk>/memorandum-signed/',
         SavioProjectReviewMemorandumSignedView.as_view(),
         name='savio-project-request-review-memorandum-signed'),
    path('savio-project-request/<int:pk>/setup/',
         SavioProjectReviewSetupView.as_view(),
         name='savio-project-request-review-setup'),
    path('savio-project-request/<int:pk>/deny/',
         SavioProjectReviewDenyView.as_view(),
         name='savio-project-request-review-deny'),
    path('savio-project-request/<int:pk>/undeny',
         SavioProjectUndenyRequestView.as_view(),
         name='savio-project-undeny-request'),
    path('project-request-vector-landing/',
         TemplateView.as_view(
             template_name=(
                 'project/project_request/vector/project_request_landing.html')
         ),
         name='project-request-vector-landing'),
    path('vector-project-request/',
         VectorProjectRequestView.as_view(),
         name='vector-project-request'),
    path('vector-project-pending-request-list/',
         VectorProjectRequestListView.as_view(completed=False),
         name='vector-project-pending-request-list'),
    path('vector-project-completed-request-list/',
         VectorProjectRequestListView.as_view(completed=True),
         name='vector-project-completed-request-list'),
    path('vector-project-request/<int:pk>/',
         VectorProjectRequestDetailView.as_view(),
         name='vector-project-request-detail'),
    path('vector-project-request/<int:pk>/eligibility',
         VectorProjectReviewEligibilityView.as_view(),
         name='vector-project-request-review-eligibility'),
    path('vector-project-request/<int:pk>/setup',
         VectorProjectReviewSetupView.as_view(),
         name='vector-project-request-review-setup'),
    path('vector-project-request/<int:pk>/undeny',
         VectorProjectUndenyRequestView.as_view(),
         name='vector-project-undeny-request'),
]


from coldfront.core.project.views_.renewal_views.approval_views import AllocationRenewalRequestListView
from coldfront.core.project.views_.renewal_views.approval_views import AllocationRenewalRequestDetailView
from coldfront.core.project.views_.renewal_views.approval_views import AllocationRenewalRequestReviewDenyView
from coldfront.core.project.views_.renewal_views.approval_views import AllocationRenewalRequestReviewEligibilityView
# This is disabled because a PI may always make a new request.
# from coldfront.core.project.views_.renewal_views.approval_views import AllocationRenewalRequestUndenyView
from coldfront.core.project.views_.renewal_views.request_views import AllocationRenewalRequestUnderProjectView
from coldfront.core.project.views_.renewal_views.request_views import AllocationRenewalRequestView


urlpatterns += [
    path('<int:pk>/renew',
         AllocationRenewalRequestUnderProjectView.as_view(),
         name='project-renew'),
    path('renew-pi-allocation-landing/',
         TemplateView.as_view(
             template_name='project/project_renewal/request_landing.html'),
         name='renew-pi-allocation-landing'),
    path('renew-pi-allocation/',
         AllocationRenewalRequestView.as_view(
             condition_dict=AllocationRenewalRequestView.condition_dict(),
         ),
         name='renew-pi-allocation'),
    path('pi-allocation-renewal-pending-request-list/',
         AllocationRenewalRequestListView.as_view(completed=False),
         name='pi-allocation-renewal-pending-request-list'),
    path('pi-allocation-renewal-completed-request-list/',
         AllocationRenewalRequestListView.as_view(completed=True),
         name='pi-allocation-renewal-completed-request-list'),
    path('pi-allocation-renewal-request-detail/<int:pk>/',
         AllocationRenewalRequestDetailView.as_view(),
         name='pi-allocation-renewal-request-detail'),
    path('pi-allocation-renewal-request/<int:pk>/eligibility/',
         AllocationRenewalRequestReviewEligibilityView.as_view(),
         name='pi-allocation-renewal-request-review-eligibility'),
    path('pi-allocation-renewal-request/<int:pk>/deny/',
         AllocationRenewalRequestReviewDenyView.as_view(),
         name='pi-allocation-renewal-request-review-deny'),
    # This is disabled because a PI may always make a new request.
    # path('pi-allocation-renewal-request/<int:pk>/undeny/',
    #      AllocationRenewalRequestUndenyView.as_view(),
    #      name='pi-allocation-renewal-request-review-undeny'),

]
