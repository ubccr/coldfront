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
    path('<int:pk>/remove-users/', project_views.ProjectRemoveUsersView.as_view(), name='project-remove-users'),
    path('<int:pk>/user-detail/<int:project_user_pk>', project_views.ProjectUserDetail.as_view(), name='project-user-detail'),
    path('<int:pk>/review/', project_views.ProjectReviewView.as_view(), name='project-review'),
    path('<int:pk>/join/', project_views.ProjectJoinView.as_view(), name='project-join'),
    path('<int:pk>/review-join-requests/', project_views.ProjectReviewJoinRequestsView.as_view(), name='project-review-join-requests'),
    path('auto-approve-join-requests/',
         project_views.ProjectAutoApproveJoinRequestsView.as_view(),
         name='project-auto-approve-join-requests'),
    path('project-review-list', project_views.ProjectReviewListView.as_view(),name='project-review-list'),
    path('project-review-complete/<int:project_review_pk>/', project_views.ProjectReviewCompleteView.as_view(),
         name='project-review-complete'),
    path('project-review/<int:pk>/email', project_views.ProjectReivewEmailView.as_view(), name='project-review-email'),

]


# TODO: Once finalized, move these imports above.
from coldfront.core.project.views import ProjectRequestView
from coldfront.core.project.views import SavioProjectRequestDetailView
from coldfront.core.project.views import SavioProjectRequestListView
from coldfront.core.project.views import SavioProjectRequestWizard
from coldfront.core.project.views import SavioProjectReviewDenyView
from coldfront.core.project.views import SavioProjectReviewEligibilityView
from coldfront.core.project.views import SavioProjectReviewReadinessView
from coldfront.core.project.views import SavioProjectReviewSetupView
from coldfront.core.project.views import show_details_form_condition
from coldfront.core.project.views import show_new_pi_form_condition
from coldfront.core.project.views import show_pooled_project_selection_form_condition
from coldfront.core.project.views import VectorProjectRequestDetailView
from coldfront.core.project.views import VectorProjectRequestListView
from coldfront.core.project.views import VectorProjectRequestView
from coldfront.core.project.views import VectorProjectReviewEligibilityView
from coldfront.core.project.views import VectorProjectReviewSetupView


urlpatterns += [
    path('project-request/',
         ProjectRequestView.as_view(),
         name='project-request'),
    path('savio-project-request/', SavioProjectRequestWizard.as_view(
        condition_dict={
            '2': show_new_pi_form_condition,
            '4': show_pooled_project_selection_form_condition,
            '5': show_details_form_condition,
            }),
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
    path('savio-project-request/<int:pk>/setup/',
         SavioProjectReviewSetupView.as_view(),
         name='savio-project-request-review-setup'),
    path('savio-project-request/<int:pk>/deny/',
         SavioProjectReviewDenyView.as_view(),
         name='savio-project-request-review-deny'),
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
]
