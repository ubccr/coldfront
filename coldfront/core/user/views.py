import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.views import PasswordChangeView
from django.db import IntegrityError
from django.db.models import BooleanField, Prefetch
from django.db.models.expressions import ExpressionWrapper, Q
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView
from django.views.generic.edit import FormView

from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.user.forms import EmailAddressAddForm
from coldfront.core.user.forms import PrimaryEmailAddressSelectionForm
from coldfront.core.user.forms import UserAccessAgreementForm
from coldfront.core.user.forms import UserProfileUpdateForm
from coldfront.core.user.forms import UserRegistrationForm
from coldfront.core.user.forms import UserSearchForm
from coldfront.core.user.models import EmailAddress
from coldfront.core.user.utils import CombinedUserSearch
from coldfront.core.user.utils import ExpiringTokenGenerator
from coldfront.core.user.utils import send_account_activation_email
from coldfront.core.user.utils import send_email_verification_email
from coldfront.core.utils.common import (import_from_settings,
                                         utc_now_offset_aware)
from coldfront.core.utils.mail import send_email_template

logger = logging.getLogger(__name__)
EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings(
        'EMAIL_TICKET_SYSTEM_ADDRESS')


@method_decorator(login_required, name='dispatch')
class UserProfile(TemplateView):
    template_name = 'user/user_profile.html'

    def dispatch(self, request, *args, viewed_username=None, **kwargs):
        # viewing another user profile requires permissions
        if viewed_username:
            if request.user.is_superuser or request.user.is_staff:
                # allow, via fallthrough
                pass
            else:
                # redirect them to their own profile

                # error if they tried to do something naughty
                if not request.user.username == viewed_username:
                    messages.error(request, "You aren't allowed to view other user profiles!")
                # if they used their own username, no need to provide an error - just redirect

                return HttpResponseRedirect(reverse('user-profile'))

        return super().dispatch(request, *args, viewed_username=viewed_username, **kwargs)

    def get_context_data(self, viewed_username=None, **kwargs):
        context = super().get_context_data(**kwargs)

        if viewed_username:
            viewed_user = get_object_or_404(User, username=viewed_username)
        else:
            viewed_user = self.request.user

        group_list = ', '.join(
            [group.name for group in viewed_user.groups.all()])
        context['group_list'] = group_list
        context['viewed_user'] = viewed_user

        context['other_emails'] = EmailAddress.objects.filter(
            user=viewed_user, is_primary=False).order_by('email')

        context['has_cluster_access'] = AllocationUserAttribute.objects.filter(
            allocation_user__user=viewed_user,
            allocation_attribute_type__name='Cluster Account Status',
            value='Active').exists()

        return context


@method_decorator(login_required, name='dispatch')
class UserProfileUpdate(TemplateView):
    template_name = 'user/user_profile_update.html'

    def post(self, request, *args, **kwargs):
        user = request.user
        user_profile_update_form = UserProfileUpdateForm(request.POST)

        if user_profile_update_form.is_valid():
            cleaned_data = user_profile_update_form.clean()
            user.first_name = cleaned_data['first_name']
            user.last_name = cleaned_data['last_name']
            user.userprofile.middle_name = cleaned_data['middle_name']
            user.userprofile.phone_number = cleaned_data['phone_number']

            user.userprofile.save()
            user.save()
            messages.success(request, 'Details updated.')
            return redirect(reverse('user-profile'))
        else:
            messages.error(request, user_profile_update_form.errors)
            return redirect(reverse('user-profile-update'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        initial_data = {'first_name': user.first_name,
                        'middle_name': user.userprofile.middle_name,
                        'last_name': user.last_name,
                        'phone_number': user.userprofile.phone_number}
        user_update_form = UserProfileUpdateForm(initial_data)
        context['user_update_form'] = user_update_form if user_update_form.is_valid() else UserProfileUpdateForm()

        return context


@method_decorator(login_required, name='dispatch')
class UserProjectsManagersView(ListView):
    template_name = 'user/user_projects_managers.html'

    def dispatch(self, request, *args, viewed_username=None, **kwargs):
        # viewing another user requires permissions
        if viewed_username:
            if request.user.is_superuser or request.user.is_staff:
                # allow, via fallthrough
                pass
            else:
                # redirect them to their own page

                # error if they tried to do something naughty
                if not request.user.username == viewed_username:
                    messages.error(request, "You aren't allowed to view projects for other users!")
                # if they used their own username, no need to provide an error - just redirect

                return HttpResponseRedirect(reverse('user-projects-managers'))

        # get_queryset does not get kwargs, so we need to store it off here
        if viewed_username:
            self.viewed_user = get_object_or_404(User, username=viewed_username)
        else:
            self.viewed_user = self.request.user

        return super().dispatch(request, *args, viewed_username=viewed_username, **kwargs)

    def get_queryset(self, *args, **kwargs):
        viewed_user = self.viewed_user

        ongoing_projectuser_statuses = (
            'Active',
            'Pending - Add',
            'Pending - Remove',
        )
        ongoing_project_statuses = (
            'New',
            'Active',
        )

        qs = ProjectUser.objects.filter(
            user=viewed_user,
            status__name__in=ongoing_projectuser_statuses,
            project__status__name__in=ongoing_project_statuses,
        ).select_related(
            'status',
            'role',
            'project',
            'project__status',
            'project__field_of_science',
        ).only(
            'status__name',
            'role__name',
            'project__title',
            'project__status__name',
            'project__field_of_science__description',
        ).annotate(
            is_project_pi=ExpressionWrapper(
                Q(role__name='Principal Investigator'),
                output_field=BooleanField(),
            ),
            is_project_manager=ExpressionWrapper(
                Q(role__name='Manager'),
                output_field=BooleanField(),
            ),
        ).order_by(
            '-is_project_pi',
            '-is_project_manager',
            Lower('project__title').asc(),
            # unlikely things will get to this point unless there's almost-duplicate projects
            '-project__pk',  # more performant stand-in for '-project__created'
        ).prefetch_related(
            Prefetch(
                lookup='project__projectuser_set',
                queryset=ProjectUser.objects.filter(
                    role__name='Principal Investigator',
                ).select_related(
                    'status',
                    'user',
                ).only(
                    'status__name',
                    'user__username',
                    'user__first_name',
                    'user__last_name',
                    'user__email',
                ).order_by(
                    'user__username',
                ),
                to_attr='project_pis',
            ),
            Prefetch(
                lookup='project__projectuser_set',
                queryset=ProjectUser.objects.filter(
                    role__name='Manager',
                    status__name__in=ongoing_projectuser_statuses,
                ).select_related(
                    'status',
                    'user',
                ).only(
                    'status__name',
                    'user__username',
                    'user__first_name',
                    'user__last_name',
                    'user__email',
                ).order_by(
                    'user__username',
                ),
                to_attr='project_managers',
            ),
        )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['viewed_user'] = self.viewed_user

        if self.request.user == self.viewed_user:
            context['user_pronounish'] = 'You'
            context['user_verbform_be'] = 'are'
        else:
            context['user_pronounish'] = 'This user'
            context['user_verbform_be'] = 'is'

        return context


# class UserUpgradeAccount(LoginRequiredMixin, UserPassesTestMixin, View):
#
#     def test_func(self):
#         return True
#
#     def dispatch(self, request, *args, **kwargs):
#         if request.user.is_superuser:
#             messages.error(request, 'You are already a super user')
#             return HttpResponseRedirect(reverse('user-profile'))
#
#         if request.user.userprofile.is_pi:
#             messages.error(request, 'Your account has already been upgraded')
#             return HttpResponseRedirect(reverse('user-profile'))
#
#         return super().dispatch(request, *args, **kwargs)
#
#     def post(self, request):
#         if EMAIL_ENABLED:
#             profile = request.user.userprofile
#
#             # request already made
#             if profile.upgrade_request is not None:
#                 messages.error(request, 'Upgrade request has already been made')
#                 return HttpResponseRedirect(reverse('user-profile'))
#
#             # make new request
#             now = datetime.utcnow().astimezone(pytz.timezone(settings.TIME_ZONE))
#             profile.upgrade_request = now
#             profile.save()
#
#             send_email_template(
#                 'Upgrade Account Request',
#                 'email/upgrade_account_request.txt',
#                 {'user': request.user},
#                 request.user.email,
#                 [EMAIL_TICKET_SYSTEM_ADDRESS]
#             )
#
#         messages.success(request, 'Your request has been sent')
#         return HttpResponseRedirect(reverse('user-profile'))


class UserSearchHome(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'user/user_search_home.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['user_search_form'] = UserSearchForm()
        return context

    def test_func(self):
        return self.request.user.is_staff


class UserSearchResults(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'user/user_search_results.html'
    raise_exception = True

    def post(self, request):
        user_search_string = request.POST.get('q')

        search_by = request.POST.get('search_by')

        cobmined_user_search_obj = CombinedUserSearch(
            user_search_string, search_by)
        context = cobmined_user_search_obj.search()

        return render(request, self.template_name, context)

    def test_func(self):
        return self.request.user.is_staff


class UserListAllocations(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'user/user_list_allocations.html'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.userprofile.is_pi

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        user_dict = {}

        project_pks = ProjectUser.objects.filter(
            user=self.request.user,
            role__name__in=['Manager', 'Principal Investigator'],
            status__name='Active').values_list('project', flat=True)
        for project in Project.objects.filter(pk__in=project_pks).distinct():
            for allocation in project.allocation_set.filter(status__name='Active'):
                for allocation_user in allocation.allocationuser_set.filter(status__name='Active').order_by('user__username'):
                    if allocation_user.user not in user_dict:
                        user_dict[allocation_user.user] = []

                    user_dict[allocation_user.user].append(allocation)

        context['user_dict'] = user_dict

        return context


class CustomPasswordChangeView(PasswordChangeView):

    template_name = 'user/passwords/password_change_form.html'
    success_url = reverse_lazy('user-profile')

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been changed.')
        return super().form_valid(form)


class UserRegistrationView(CreateView):

    form_class = UserRegistrationForm
    template_name = 'user/registration.html'
    success_url = reverse_lazy('register')

    def form_valid(self, form):
        self.object = form.save()

        send_account_activation_email(self.object)
        message = (
            'Thank you for registering. Please click the link sent to your '
            'email address to activate your account.')
        messages.success(self.request, message)

        return HttpResponseRedirect(self.get_success_url())


def activate_user_account(request, uidb64=None, token=None):
    logger = logging.getLogger(__name__)
    try:
        user_pk = int(force_text(urlsafe_base64_decode(uidb64)))
        user = User.objects.get(pk=user_pk)
    except:
        user = None
    if user and token:
        if PasswordResetTokenGenerator().check_token(user, token):
            # Create or update an EmailAddress for the user's provided email.
            try:
                email_address, created = EmailAddress.objects.get_or_create(
                    user=user, email=user.email)
            except Exception as e:
                logger.error(
                    f'Failed to create EmailAddress for User {user.pk} and '
                    f'email {user.email}. Details:')
                logger.exception(e)
                message = (
                    'Unexpected server error. Please contact an '
                    'administrator.')
                messages.error(request, message)
            else:
                if created:
                    logger.info(
                        f'Created EmailAddress {email_address.pk} for User '
                        f'{user.pk} and email {user.email}.')
                email_address.is_verified = True
                email_address.is_primary = True
                email_address.save()

                # Only activate the User if the EmailAddress update succeeded.
                user.is_active = True
                user.save()

                message = (
                    f'Your account has been activated. You may now log in. '
                    f'{user.email} has been verified and set as your primary '
                    f'email address. You may modify this in the User Profile.')
                messages.success(request, message)
        else:
            message = (
                'Invalid activation token. Please try again, or contact an '
                'administrator if the problem persists.')
            messages.error(request, message)
    else:
        message = (
            'Failed to activate account. Please contact an administrator.')
        messages.error(request, message)
    return redirect(reverse('login'))


@login_required
def user_access_agreement(request):
    profile = request.user.userprofile
    if profile.access_agreement_signed_date is not None:
        message = 'You have already signed the user access agreement form.'
        messages.warning(request, message)
    if request.method == 'POST':
        form = UserAccessAgreementForm(request.POST)
        if form.is_valid():
            now = utc_now_offset_aware()
            profile.access_agreement_signed_date = now
            profile.save()
            message = 'Thank you for signing the user access agreement form.'
            messages.success(request, message)
            return redirect(reverse_lazy('home'))
        else:
            message = 'Incorrect answer. Please try again.'
            messages.error(request, message)
    else:
        form = UserAccessAgreementForm()
    return render(request, 'user/user_access_agreement.html', {'form': form})


class EmailAddressAddView(LoginRequiredMixin, FormView):
    form_class = EmailAddressAddForm
    template_name = 'user/user_add_email_address.html'

    logger = logging.getLogger(__name__)

    def form_valid(self, form):
        form_data = form.cleaned_data
        email = form_data['email']
        try:
            email_address = EmailAddress.objects.create(
                user=self.request.user, email=email, is_verified=False,
                is_primary=False)
        except IntegrityError:
            self.logger.error(
                f'EmailAddress {email} unexpectedly already exists.')
            message = (
                'Unexpected server error. Please contact an administrator.')
            messages.error(self.request, message)
        else:
            self.logger.info(
                f'Created EmailAddress {email_address.pk} for User '
                f'{self.request.user.pk}.')
            try:
                send_email_verification_email(email_address)
            except Exception as e:
                message = 'Failed to send verification email. Details:'
                logger.error(message)
                logger.exception(e)
                message = (
                    f'Added {email_address.email} to your account, but failed '
                    f'to send verification email. You may try to resend it '
                    f'from the User Profile.')
                messages.warning(self.request, message)
            else:
                message = (
                    f'Added {email_address.email} to your account. Please '
                    f'verify it by clicking the link sent to your email.')
                messages.success(self.request, message)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('user-profile')


class SendEmailAddressVerificationEmailView(LoginRequiredMixin, View):

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.email_address = get_object_or_404(EmailAddress, pk=pk)
        if self.email_address.user != request.user:
            message = (
                'You may not send a verification email to an email address '
                'not associated with your account.')
            messages.error(request, message)
            return HttpResponseRedirect(reverse('user-profile'))
        if self.email_address.is_verified:
            logger.error(
                f'EmailAddress {self.email_address.pk} is unexpectedly '
                f'already verified.')
            message = f'{self.email_address.email} is already verified.'
            messages.warning(request, message)
            return HttpResponseRedirect(reverse('user-profile'))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            send_email_verification_email(self.email_address)
        except Exception as e:
            message = 'Failed to send verification email. Details:'
            logger.error(message)
            logger.exception(e)
            message = (
                f'Failed to send verification email to '
                f'{self.email_address.email}. Please contact an administrator '
                f'if the problem persists.')
            messages.error(request, message)
        else:
            message = (
                f'Please click on the link sent to {self.email_address.email} '
                f'to verify it.')
            messages.success(request, message)
        return HttpResponseRedirect(reverse('user-profile'))


def verify_email_address(request, uidb64=None, eaidb64=None, token=None):
    try:
        user_pk = int(force_text(urlsafe_base64_decode(uidb64)))
        email_pk = int(force_text(urlsafe_base64_decode(eaidb64)))
        email_address = EmailAddress.objects.get(pk=email_pk)
        user = User.objects.get(pk=user_pk)
        if email_address.user != user:
            user = None
    except:
        user = None
    if user and token:
        if ExpiringTokenGenerator().check_token(user, token):
            email_address.is_verified = True
            email_address.save()
            logger.info(f'EmailAddress {email_address.pk} has been verified.')
            message = f'{email_address.email} has been verified.'
            messages.success(request, message)
        else:
            message = (
                'Invalid verification token. Please try again, or contact an '
                'administrator if the problem persists.')
            messages.error(request, message)
    else:
        message = (
            f'Failed to activate account. Please contact an administrator.')
        messages.error(request, message)
    return redirect(reverse('user-profile'))


class RemoveEmailAddressView(LoginRequiredMixin, View):

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.email_address = get_object_or_404(EmailAddress, pk=pk)
        if self.email_address.user != request.user:
            message = (
                'You may not remove an email address not associated with your '
                'account.')
            messages.error(request, message)
            return HttpResponseRedirect(reverse('user-profile'))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.email_address.delete()
        message = (
            f'{self.email_address.email} has been removed from your account.')
        messages.success(request, message)
        return HttpResponseRedirect(reverse('user-profile'))


class UpdatePrimaryEmailAddressView(LoginRequiredMixin, FormView):

    form_class = PrimaryEmailAddressSelectionForm
    template_name = 'user/user_update_primary_email_address.html'
    login_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_verified_non_primary_emails'] = \
            EmailAddress.objects.filter(
                user=self.request.user, is_verified=True, is_primary=False)
        return context

    def form_valid(self, form):
        # Set the old primary address as no longer primary.
        user = self.request.user
        old = user.email
        old_primary, created = EmailAddress.objects.get_or_create(
            user=user, email=old)
        if created:
            message = (
                f'Created EmailAddress {old_primary.pk} for User '
                f'{user.pk}\'s old primary address {old}, which unexpectedly '
                f'did not exist.')
            logger.warning(message)
        old_primary.is_primary = False
        old_primary.save()
        # Set the new primary address as primary.
        form_data = form.cleaned_data
        new_primary = form_data['email_address']
        if not new_primary.is_verified:
            message = (
                f'New primary EmailAddress {new_primary.pk} for User '
                f'{user.pk} is unexpectedly not verified.')
            logger.error(message)
            message = (
                'Unexpected server error. Please contact an administrator.')
            messages.error(self.request, message)
        else:
            new_primary.is_primary = True
            new_primary.save()
            message = f'{new_primary.email} is your new primary email address.'
            messages.success(self.request, message)
            # Set the User's email field.
            user.email = new_primary.email
            user.save()
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('user-profile')
