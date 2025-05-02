import abc
import logging

from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.module_loading import import_string

from coldfront.core.utils.common import import_from_settings

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
            entries = User.objects.all()[:size_limit]

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
        logger.info("Starting CombinedUserSearch initialization")
        
        self.USER_SEARCH_CLASSES = []
        
        # Always add local search first
        local_search = 'coldfront.core.user.utils.LocalUserSearch'
        self.USER_SEARCH_CLASSES.append(local_search)
        logger.debug(f"Added local search: {local_search}")

        # Add LDAP search if enabled
        if getattr(settings, 'PLUGIN_LDAP_USER_SEARCH', False):
            ldap_search = 'coldfront.plugins.ldap_user_search.utils.LDAPUserSearch'
            self.USER_SEARCH_CLASSES.append(ldap_search)
            logger.debug(f"Added LDAP search: {ldap_search}")
            
        logger.debug(f"Final search classes: {self.USER_SEARCH_CLASSES}")
        
        self.user_search_string = user_search_string
        self.search_by = search_by
        self.usernames_names_to_exclude = usernames_names_to_exclude

    def search(self):
        matches = []
        usernames_not_found = []
        usernames_found = []

        logger.info("Starting user search process")
        
        # First try local search
        local_search_class = self.USER_SEARCH_CLASSES[0]  # Local search is always first
        try:
            cls = import_string(local_search_class)
            search_class_obj = cls(self.user_search_string, self.search_by)
            logger.debug(f"Initialized local search class object: {cls.__name__}")
            
            local_users = search_class_obj.search()
            if local_users:
                logger.info(f"Local search found {len(local_users)} users")
                matches.extend(local_users)
                
        except Exception as e:
            logger.error(
                f"Error processing local search class {local_search_class}: {str(e)}", 
                exc_info=True
            )

        # Only proceed with LDAP search if no local matches were found
        if not matches and len(self.USER_SEARCH_CLASSES) > 1:
            ldap_search_class = self.USER_SEARCH_CLASSES[1]
            try:
                cls = import_string(ldap_search_class)
                search_class_obj = cls(self.user_search_string, self.search_by)
                logger.debug(f"Initialized LDAP search class object: {cls.__name__}")
                
                ldap_users = search_class_obj.search()
                if ldap_users:
                    logger.info(f"LDAP search found {len(ldap_users)} users")
                    matches.extend(ldap_users)
                else:
                    logger.debug("No users found in LDAP search")
                    
            except Exception as e:
                logger.error(
                    f"Error processing LDAP search class {ldap_search_class}: {str(e)}", 
                    exc_info=True
                )

        return {
            'matches': matches,
            'usernames_not_found': usernames_not_found,
            'usernames_found': usernames_found
        }
