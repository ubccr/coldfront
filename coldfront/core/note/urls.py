from django.urls import path
import coldfront.core.note.views as note_views
import coldfront.core.allocation.views as allocation_views

urlpatterns = [
    path('add-allocation-note/<int:allocation_pk>/', note_views.NoteCreateView.as_view(), name='add-allocation-notes_app'),
    path('note-detail/<int:pk>/', note_views.AllocationNoteDetailView.as_view(), name="allocation-notes-detail"),
    path('add-comment/<int:pk>/', note_views.CommentCreateView.as_view(), name='add-comment'),

    # path('<int:allocation_pk>/', allocation_views.AllocationDetailView.as_view(),
    #      name='allocation-detail'),
]