import abc
import logging

from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db.models import Q
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.module_loading import import_string

from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template

from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class UserSearch(abc.ABC):

    def __init__(self, user_search_string, search_by):
        self.user_search_string = user_search_string
        self.search_by = search_by

    @abc.abstractmethod
    def search_a_user(self, user_search_string=None, search_by='all_fields'):
        pass

    def search(self):
        if len(self.user_search_string.split()) > 1:
            search_by = 'username_only'
            matches = []
            number_of_usernames_found = 0
            users_not_found = []

            user_search_string = sorted(list(set(self.user_search_string.split())))
            for username in user_search_string:
                match = self.search_a_user(username, search_by)
                if match:
                    matches.extend(match)
        else:
            matches = self.search_a_user(self.user_search_string, self.search_by)

        return matches


class LocalUserSearch(UserSearch):
    search_source = 'local'

    def search_a_user(self, user_search_string=None, search_by='all_fields'):
        size_limit = 50
        if user_search_string and search_by == 'all_fields':
            entries = User.objects.filter(
                Q(username__icontains=user_search_string) |
                Q(first_name__icontains=user_search_string) |
                Q(last_name__icontains=user_search_string) |
                Q(email__icontains=user_search_string)
            ).filter(Q(is_active=True)).distinct()[:size_limit]

        elif user_search_string and search_by == 'username_only':
            entries = User.objects.filter(username=user_search_string, is_active=True)
        else:
            User.objects.all()[:size_limit]

        users = []
        for idx, user in enumerate(entries, 1):
            if user:
                user_dict = {
                    'last_name': user.last_name,
                    'first_name': user.first_name,
                    'username': user.username,
                    'email': user.email,
                    'source': self.search_source,
                }
                users.append(user_dict)

        logger.info("Local user search for %s found %s results", user_search_string, len(users))
        return users


class CombinedUserSearch:

    def __init__(self, user_search_string, search_by, usernames_names_to_exclude=[]):
        self.USER_SEARCH_CLASSES = import_from_settings('ADDITIONAL_USER_SEARCH_CLASSES', [])
        self.USER_SEARCH_CLASSES.insert(0, 'coldfront.core.user.utils.LocalUserSearch')
        self.user_search_string = user_search_string
        self.search_by = search_by
        self.usernames_names_to_exclude = usernames_names_to_exclude

    def search(self):

        matches = []
        usernames_not_found = []
        usernames_found = []


        for search_class in self.USER_SEARCH_CLASSES:
            cls = import_string(search_class)
            search_class_obj = cls(self.user_search_string, self.search_by)
            users = search_class_obj.search()

            for user in users:
                username = user.get('username')
                if username not in usernames_found and username not in self.usernames_names_to_exclude:
                    usernames_found.append(username)
                    matches.append(user)

        if len(self.user_search_string.split()) > 1:
            number_of_usernames_searched = len(self.user_search_string.split())
            number_of_usernames_found = len(usernames_found)
            usernames_not_found = list(set(self.user_search_string.split()) - set(usernames_found) - set(self.usernames_names_to_exclude))
        else:
            number_of_usernames_searched = None
            number_of_usernames_found = None
            usernames_not_found = None

        context = {
            'matches': matches,
            'number_of_usernames_searched': number_of_usernames_searched,
            'number_of_usernames_found': number_of_usernames_found,
            'usernames_not_found': usernames_not_found
        }
        return context


def __account_activation_url(user):
    domain = import_from_settings('CENTER_BASE_URL')
    uidb64 = urlsafe_base64_encode(force_bytes(user.id))
    token = PasswordResetTokenGenerator().make_token(user)
    kwargs = {
        'uidb64': uidb64,
        'token': token,
    }
    view = reverse('activate', kwargs=kwargs)
    return urljoin(domain, view)


def send_account_activation_email(user):
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = 'Account Activation Required'
    template_name = 'email/account_activation_required.txt'
    context = {
        'center_name': import_from_settings('CENTER_NAME', ''),
        'activation_url': __account_activation_url(user),
        'signature': import_from_settings('EMAIL_SIGNATURE', ''),
    }
    sender = import_from_settings('EMAIL_SENDER', ''),
    receiver_list = [user.email, ]

    send_email_template(subject, template_name, context, sender, receiver_list)
