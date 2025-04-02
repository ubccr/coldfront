from django.urls import path

from coldfront.plugins.announcements import views


urlpatterns = [
    path('', views.AnnouncementsView.as_view() , name='announcement-list'),
    path('filter', views.AnnouncementListView.as_view() , name='announcement-filter'),
    path('create', views.AnnouncementCreateView.as_view(), name='announcement-create'),
    path('read', views.AnnouncementReadView.as_view(), name='announcement-read'),
    path('update/<int:pk>/', views.AnnouncementUpdateView.as_view(), name='announcement-update'),
]
