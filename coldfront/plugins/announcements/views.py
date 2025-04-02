import logging
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import ListView, UpdateView, FormView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from coldfront.core.utils.mail import send_email_template
from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.announcements.models import Announcement, AnnouncementCategoryChoice, AnnouncementMailingListChoice, AnnouncementStatusChoice
from coldfront.plugins.announcements.forms import AnnouncementCreateForm, AnnouncementFilterForm

logger = logging.getLogger(__name__)

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_CENTER_NAME = import_from_settings('CENTER_NAME')
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')



class AnnouncementsView(LoginRequiredMixin, TemplateView):
    template_name = 'announcements/announcements.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_user'] = self.request.user
        context['categories'] = {category.pk: category.name for category in AnnouncementCategoryChoice.objects.all()}

        announcement_filter_form = AnnouncementFilterForm(self.request.GET)
        if not announcement_filter_form.is_valid():
            announcement_filter_form = AnnouncementFilterForm()

        context['filter_form'] = announcement_filter_form

        return context


class AnnouncementListView(LoginRequiredMixin, ListView):
    model=Announcement
    template_name = 'announcements/announcement_list.html'
    context_object_name = "announcements"
    paginate_by = 5

    def dispatch(self, request, *args, **kwargs):
        if request.META.get('HTTP_REFERER') is None:
            return HttpResponseNotFound(render(request, '404.html', {}))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        announcements = Announcement.objects.filter(status__name='Active').order_by('-pinned', '-created')

        announcement_filter_form = AnnouncementFilterForm(self.request.GET)
        if announcement_filter_form.is_valid():
            data = announcement_filter_form.cleaned_data
            if data.get('title'):
                announcements = announcements.filter(title__icontains=data.get('title'))
            if data.get('categories'):
                for categories in data.get('categories'):
                    announcements = announcements.filter(categories=categories)

        return announcements


class AnnouncementCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = AnnouncementCreateForm
    template_name = "announcements/announcement_create_form.html"

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('announcements.add_announcement'):
            return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = {category.pk: category.name for category in AnnouncementCategoryChoice.objects.all()}
        context['mailing_lists'] = {mailing_list.pk: mailing_list.name for mailing_list in AnnouncementMailingListChoice.objects.all()}

        return context

    def form_valid(self, form):
        data = form.cleaned_data
        mailing_list = data.get('mailing_lists')
        announcement_obj = Announcement.objects.create(
            title = data.get('title'),
            body = data.get('body'),
            status = AnnouncementStatusChoice.objects.get(name='Active'),
            details_url = data.get('details_url'),
            author = self.request.user,
            pinned = data.get('pinned')
        )

        announcement_obj.categories.set(data.get('categories'))
        announcement_obj.mailing_lists.set(mailing_list)

        logger.info(f'Admin {self.request.user.username} created a new announcement, pk={announcement_obj.pk}')

        if mailing_list:
            for mailing_list in mailing_list:
                context = {
                    'center_name': EMAIL_CENTER_NAME,
                    'announcement': data.get('body'),
                    'signature': EMAIL_SIGNATURE
                }
                send_email_template(
                    subject=data.get('title'),
                    template_name='announcements/announcement_created.txt',
                    template_context=context,
                    sender=self.request.user.email,
                    receiver_list=[mailing_list.value]
                )

        return super().form_valid(form)

    def get_success_url(self):
        msg = 'Announcement has been created.'
        messages.success(self.request, msg)
        return reverse('announcement-list') 


class AnnouncementUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Announcement
    fields = ['title', 'body', 'categories', 'mailing_lists', 'details_url', 'status', 'pinned']
    template_name_suffix='_update_form'

    def test_func(self):
        announcement_obj = get_object_or_404(Announcement, pk=self.kwargs.get('pk'))
        if self.request.user.is_superuser:
            return True

        if not self.request.user == announcement_obj.author:
            messages.error(self.request, 'You can only update your own announcements.')
            return

        if self.request.user.has_perm('announcements.change_announcement'):
            return True

        if not announcement_obj.status.name == 'Active':
            messages.error(self.request, 'You can only update active announcements.')
            return

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        announcement_obj = get_object_or_404(Announcement, pk=self.kwargs.get('pk'))

        context['categories'] = {category.pk: category.name for category in AnnouncementCategoryChoice.objects.all()}
        context['initial_categories_selected'] = list(announcement_obj.categories.all().values_list('pk', flat=True))
        context['mailing_lists'] = {mailing_list.pk: mailing_list.name for mailing_list in AnnouncementMailingListChoice.objects.all()}
        context['initial_mailing_lists_selected'] = list(announcement_obj.mailing_lists.all().values_list('pk', flat=True))
        context['pk'] = announcement_obj.pk

        return context

    def get_success_url(self):
        logger.info(f'Admin {self.request.user.username} updated an announcement, pk={self.object.pk}')
        messages.success(self.request, 'Your announcement has been updated.')
        return reverse('announcement-list')


class AnnouncementReadView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        announcement_objs = Announcement.objects.filter(status__name='Active')
        for announcement_obj in announcement_objs:
            announcement_obj.viewed_by.add(request.user)
        return HttpResponseRedirect(reverse('announcement-list'))

    def post(self, request, *args, **kwargs):
        announcement_obj = Announcement.objects.get(pk=request.POST.get('pk'))
        announcement_obj.viewed_by.add(request.user)
        logger.info(f'User {self.request.user.username} marked announcement {announcement_obj.pk} as read')
        return render(request, 'announcements/navbar_announcements_unread.html', {'user': self.request.user})
