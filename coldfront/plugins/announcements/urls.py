from django.urls import path

from coldfront.plugins.announcements import views


urlpatterns = [
    path('', views.AnnouncementListView.as_view() , name='announcement-list'),
    path('create', views.AnnouncementCreateView.as_view(), name='announcement-create'),
    path('update/<int:pk>/', views.AnnouncementUpdateView.as_view(), name='announcement-update'),
    path('delete/<int:pk>/', views.AnnouncementDeleteView.as_view(), name='announcement-delete'),
]
