import json
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, UpdateView, DeleteView, DetailView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from coldfront.plugins.announcements.models import Announcement, AnnouncementCategoryChoice, AnnouncementMailingListChoice, AnnouncementStatusChoice
from coldfront.plugins.announcements.forms import AnnouncementCreateForm, AnnouncementFilterForm


class AnnouncementListView(LoginRequiredMixin, ListView):
    model=Announcement
    template_name = 'announcements/announcement_list.html'
    context_object_name = "announcements"
    paginate_by = 5

    def get_queryset(self):
        announcements = Announcement.objects.all()

        announcement_filter_form = AnnouncementFilterForm(self.request.GET)
        if announcement_filter_form.is_valid():
            data = announcement_filter_form.cleaned_data
            if data.get('categories'):
                announcements = announcements.filter(categories__in=data.get('categories'))

        return announcements

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_user'] = self.request.user.username
        context['selections'] = json.dumps({
            'categories': {
                'full_list': list(AnnouncementCategoryChoice.objects.all().values_list('name', flat=True)),
                'available': [],
                'selected': [],
                'name': 'categories'
            },
        })
        
        announcement_filter_form = AnnouncementFilterForm(self.request.GET)
        if not announcement_filter_form.is_valid():
            announcement_filter_form = AnnouncementFilterForm()

        context['filter_form'] = announcement_filter_form

        return context


class AnnouncementDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model=Announcement
    context_object_name = "announcement"

    def test_func(self):
        pk = self.kwargs.get('pk')
        announcement_obj = get_object_or_404(Announcement, pk=pk)

        if self.request.user.is_superuser:
            return True


class AnnouncementCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = AnnouncementCreateForm
    template_name = "announcements/announcement_create_form.html"

    def test_func(self):
        if self.request.user.is_superuser:
            return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selections'] = json.dumps({
            'categories': {
                'full_list': list(AnnouncementCategoryChoice.objects.all().values_list('name', flat=True)),
                'available': [],
                'selected': []
            },
            'mailing_lists': {
                'full_list': list(AnnouncementMailingListChoice.objects.all().values_list('name', flat=True)),
                'available': [],
                'selected': []
            },
        })

        return context
    
    def form_valid(self, form):
        data = form.cleaned_data
        announcement_obj = Announcement.objects.create(
            title = data.get('title'),
            body = data.get('body'),
            status = AnnouncementStatusChoice.objects.get(name='Active'),
        )

        announcement_obj.categories.set(data.get('categories'))
        announcement_obj.mailing_lists.set(data.get('mailing_lists'))


        if data.get('mailing_lists'):
            pass

        return super().form_valid(form)
    
    def get_success_url(self):
        msg = 'Announcement has been created.'
        messages.success(self.request, msg)
        return reverse('announcement-list') 


class AnnouncementUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model=Announcement
    context_object_name = "announcement"

    def test_func(self):
        pk = self.kwargs.get('pk')
        announcement_obj = get_object_or_404(Announcement, pk=pk)

        if self.request.user.is_superuser:
            return True


class AnnouncementDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model=Announcement
    context_object_name = "announcement"

    def test_func(self):
        pk = self.kwargs.get('pk')
        announcement_obj = get_object_or_404(Announcement, pk=pk)

        if self.request.user.is_superuser:
            return True


class AnnouncementCategorySearchView(View):
    pass