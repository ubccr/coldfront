from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.management.commands.utils import get_gspread_worksheet
from coldfront.core.utils.management.commands.utils import get_gspread_worksheet_data
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.core.validators import validate_email
import logging
import os

"""An admin command that creates existing users and accounts for BRC."""


CLUSTERS = {'cortex', 'savio', 'vector'}

PASSWD_FILE = '/tmp/passwd'

PROJECT_ALLOWANCES = {
    'ac_': 'allowance_has_recharge',
    'co_': 'allowance_has_condo',
    'fc_': 'allowance_has_pca',
    'ic_': 'allowance_has_instructional',
    'pc_': 'allowance_has_partner'
}

PROJECT_PREFIXES = {'ac_', 'cortex', 'co_', 'fc_', 'ic_', 'pc_', 'vector_'}

PROJECT_PREFIXES_BY_CLUSTER = {
    'cortex': {'cortex'},
    'savio': {'ac_', 'co_', 'fc_', 'ic_', 'pc_'},
    'vector': {'vector_'}
}

# Settings for the 'All-Projects' tab of the 'BRC-Projects' spreadsheet.
PROJECT_SPREADSHEET_COLS = {
    'NAME': 3,
    'POC_NAMES': 4,
    'POC_EMAILS': 5,
    'PI_NAMES': 6,
    'PI_EMAILS': 7
}
PROJECT_SPREADSHEET_ID = '1N6VT5VHN07z4nXhea5AXQXRF8WUDoHbJwWL4PV3C66M'
PROJECT_SPREADSHEET_ROW_START = 2
PROJECT_SPREADSHEET_TAB = 'All-Projects'

# Settings for the 'All-Users' tab of the 'BRC-Users' spreadsheet.
USER_SPREADSHEET_COLS = {
    'USERNAME': 1,
    'NAME': 2,
    'EMAIL': 3,
    'CLUSTERS': 4
}
USER_SPREADSHEET_ID = '1zvTLSbUNtoBoSQcMCdOlJTm8OvvwWnlfP2_0gQLibR8'
USER_SPREADSHEET_ROW_START = 2
USER_SPREADSHEET_TAB = 'All-Users'

# Settings for the 'Savio-users' tab of the 'BRC-Users' spreadsheet.
USER_PROJECT_SPREADSHEET_COLS = {
    'NAME': 1,
    'EMAIL': 2,
    'USERNAME': 3,
    'PROJECTS': 4
}
USER_PROJECT_SPREADSHEET_ROW_START = 2
USER_PROJECT_SPREADSHEET_TAB = 'Savio-users'


class Command(BaseCommand):

    help = 'Creates users and accounts from the BRC spreadsheets.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        # Create Users.
        user_data = self.get_user_data()
        valid_users = self.get_valid_users(user_data)
        self.create_users(valid_users)
        # Create Projects and associate PI and POC Users with them.
        project_data = self.get_project_data()
        valid_projects = self.get_valid_projects(project_data)
        self.create_projects(valid_projects)
        # Associate remaining Users with Projects (both of which should
        # already exist).
        user_project_data = self.get_user_project_data()
        valid_user_projects = self.get_valid_user_projects(user_project_data)
        self.create_project_users(valid_user_projects)

    def create_project_users(self, valid_user_projects):
        """Create ProjectUser objects given a list of dictionaries where
        each entry corresponds to a valid user and contains projects the
        user is a member of.

        Parameters:
            - valid_user_projects (list): a list of dictionaries

        Returns:
            - None

        Raises:
            - Exception, if any errors occur
        """
        role = ProjectUserRoleChoice.objects.get(name='User')
        status = ProjectUserStatusChoice.objects.get(name='Active')
        for valid_user_project in valid_user_projects:
            username = valid_user_project['username']
            projects = valid_user_project['projects']
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.logger.error(f'User {username} does not exist.')
                continue
            for project_name in [name.strip() for name in projects.split(',')]:
                try:
                    project = Project.objects.get(name=project_name)
                except Project.DoesNotExist:
                    self.logger.error(
                        f'Project {project_name} does not exist.')
                    continue
                if not ProjectUser.objects.filter(user=user, project=project):
                    ProjectUser.objects.create(
                        user=user, project=project, role=role, status=status)
                    self.logger.info(
                        f'Created a ProjectUser between User {user.username} '
                        f'and Project {project.name}.')

    def create_projects(self, valid_projects):
        """Create Project, User, and ProjectUser objects given a list of
        dictionaries where each entry corresponds to a valid project.

        Parameters:
            - valid_projects (list): a list of dictionaries

        Returns:
            - None

        Raises:
            - Exception, if any errors occur
        """
        project_status = ProjectStatusChoice.objects.get(name='Active')
        principal_investigator_role = \
            ProjectUserRoleChoice.objects.get(name='Principal Investigator')
        manager_role = ProjectUserRoleChoice.objects.get(name='Manager')
        project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')

        for valid_project in valid_projects:
            name = valid_project['name']
            poc_names = valid_project['poc_names']
            poc_emails = valid_project['poc_emails']
            pi_names = valid_project['pi_names']
            pi_emails = valid_project['pi_emails']

            # Create User objects for faculty and grant them PI status.
            PIs = set()
            for i, pi_email in enumerate(pi_emails):
                # If the user already exists, retrieve its username. Otherwise,
                # use the email address as username.
                try:
                    user = User.objects.get(email=pi_email)
                    username = user.username
                except User.DoesNotExist:
                    username = pi_email
                pi_split_names = self.get_first_middle_last_names(pi_names[i])
                user_kwargs = {
                    'email': pi_email,
                    'first_name': pi_split_names['first'],
                    'last_name': pi_split_names['last'],
                }
                pi, created = User.objects.get_or_create(username=username)
                if created:
                    self.logger.info(f'User {username} was created.')
                for key, value in user_kwargs.items():
                    setattr(pi, key, value)
                pi.save()
                PIs.add(pi)

                user_profile_kwargs = {
                    'user': pi,
                    'middle_name': pi_split_names['middle'],
                    'is_pi': True,
                }
                user_profile, created = UserProfile.objects.get_or_create(
                    user=pi)
                if created:
                    self.logger.info(
                        f'UserProfile for user {pi.username} was created.')
                for key, value in user_profile_kwargs.items():
                    setattr(user_profile, key, value)
                user_profile.save()
            PIs = sorted(list(PIs), key=lambda pi: pi.username)

            # Choose the appropriate display name.
            title = name

            # Create the project.
            project_kwargs = {
                'title': title,
                'status': project_status,
            }
            try:
                project = Project.objects.get(name=name)
            except Project.DoesNotExist:
                project = Project.objects.create(
                    name=name, title=title, status=project_status)
                self.logger.info(f'Project {name} was created.')
            else:
                for key, value in project_kwargs.items():
                    setattr(project, key, value)
                project.save()

            # Set faculty as PIs.
            for pi in PIs:
                try:
                    project_user = ProjectUser.objects.get(
                        user=pi, project=project)
                except ProjectUser.DoesNotExist:
                    ProjectUser.objects.create(
                        user=pi, project=project,
                        role=principal_investigator_role,
                        status=project_user_status)
                    self.logger.info(
                        f'Created a ProjectUser between User {pi.username} '
                        f'and Project {project.name}.')
                else:
                    project_user.role = principal_investigator_role
                    project_user.status = project_user_status
                    project_user.save()

            # Set main contacts as Managers.
            for i, poc_name in enumerate(poc_names):
                poc_split_name = self.get_first_middle_last_names(poc_name)
                email = poc_emails[i]
                user_kwargs = {
                    'email': email,
                    'first_name': poc_split_name['first'],
                    'last_name': poc_split_name['last']
                }

                # If the user already exists, retrieve its username. Otherwise,
                # use the email address as username.
                try:
                    user = User.objects.get(email=email)
                    username = user.username
                except User.DoesNotExist:
                    username = email

                poc, created = User.objects.get_or_create(username=username)
                if created:
                    self.logger.info(f'User {username} was created.')
                for key, value in user_kwargs.items():
                    setattr(poc, key, value)
                poc.save()

                user_profile_kwargs = {
                    'middle_name': poc_split_name['middle'],
                }
                user_profile, created = UserProfile.objects.get_or_create(
                    user=poc)
                if created:
                    self.logger.info(
                        f'UserProfile for user {poc.username} was created.')
                for key, value in user_profile_kwargs.items():
                    setattr(user_profile, key, value)
                user_profile.save()

                try:
                    project_user = ProjectUser.objects.get(
                        user=poc, project=project)
                except ProjectUser.DoesNotExist:
                    ProjectUser.objects.create(
                        user=poc, project=project, role=manager_role,
                        status=project_user_status)
                    self.logger.info(
                        f'Created a ProjectUser between User {poc.username} '
                        f'and Project {project.name}.')
                else:
                    if project_user.role != principal_investigator_role:
                        project_user.role = manager_role
                    project_user.status = project_user_status
                    project_user.save()

    def create_users(self, valid_users):
        """Create User objects given a list of dictionaries where each
        entry corresponds to a valid user.

        Parameters:
            - valid_users (list): a list of dictionaries

        Returns:
            - None

        Raises:
            - Exception, if any errors occur
        """
        for valid_user in valid_users:
            username = valid_user['username']
            user_kwargs = {
                'email': valid_user['email'],
                'first_name': valid_user['first_name'],
                'last_name': valid_user['last_name'],
            }

            user, created = User.objects.get_or_create(username=username)
            if created:
                self.logger.info(f'User {username} was created.')
            for key, value in user_kwargs.items():
                setattr(user, key, value)
            user.save()

            user_profile_kwargs = {
                'middle_name': valid_user['middle_name'],
                'cluster_uid': valid_user['cluster_uid'],
            }
            user_profile, created = UserProfile.objects.get_or_create(
                user=user)
            if created:
                self.logger.info(
                    f'UserProfile for user {user.username} was created.')
            for key, value in user_profile_kwargs.items():
                setattr(user_profile, key, value)
            user_profile.save()

    @staticmethod
    def file_exists(file_path):
        """Return whether or not the object at the given path is an
        existing file.

        Parameters:
            - file_path (str): the path to the file to test

        Returns:
            - Boolean

        Raises:
            - None
        """
        return os.path.exists(file_path) and os.path.isfile(file_path)

    @staticmethod
    def get_first_middle_last_names(full_name):
        """Return the given full name split into first, middle, and last
        in a dictionary.

        Parameters:
            - full_name (str): A name with potentially first, middle,
                               and last components

        Returns:
            - Dictionary with 'first', 'middle', and 'last' fields

        Raises:
            - None
        """
        names = {
            'first': '',
            'middle': '',
            'last': ''
        }
        full_name = full_name.strip().split()
        if not full_name:
            return names
        names['first'] = full_name[0]
        if len(full_name) == 2:
            names['last'] = full_name[-1]
        else:
            names['middle'] = ' '.join(full_name[1:-1])
            names['last'] = full_name[-1]
        return names

    @staticmethod
    def get_project_data():
        """Return a list of lists where each entry corresponds to a
        single project from the project spreadsheet.

        Parameters:
            - None

        Returns:
            - List of lists

        Raises:
            - Exception, if any errors occur
        """
        worksheet = get_gspread_worksheet(
            settings.GOOGLE_OAUTH2_KEY_FILE, PROJECT_SPREADSHEET_ID,
            PROJECT_SPREADSHEET_TAB)
        row_start = PROJECT_SPREADSHEET_ROW_START
        row_end = len(worksheet.col_values(PROJECT_SPREADSHEET_COLS['NAME']))
        col_start = 1
        col_end = worksheet.col_count
        return get_gspread_worksheet_data(
            worksheet, row_start, row_end, col_start, col_end)

    @staticmethod
    def get_user_data():
        """Return a list of lists where each entry corresponds to a
        single user from the user worksheet.

        Parameters:
            - None

        Returns:
            - List of lists

        Raises:
            - Exception, if any errors occur
        """
        worksheet = get_gspread_worksheet(
            settings.GOOGLE_OAUTH2_KEY_FILE, USER_SPREADSHEET_ID,
            USER_SPREADSHEET_TAB)
        row_start = USER_SPREADSHEET_ROW_START
        row_end = len(worksheet.col_values(USER_SPREADSHEET_COLS['USERNAME']))
        col_start = 1
        col_end = USER_SPREADSHEET_COLS['CLUSTERS']
        return get_gspread_worksheet_data(
            worksheet, row_start, row_end, col_start, col_end)

    def get_user_ids(self, password_file_path):
        """Parse the password file at the given path and return a
        mapping from user_username to user_id. Each line of the password
        file has 7 entries delimited by ':'. The first is the user's
        username. The third is a non-negative user ID.

        Parameters:
            - password_file_path (str): the path to the password file

        Returns:
            - Dictionary mapping username to ID

        Raises:
            - None
        """
        user_data = {}
        if self.file_exists(password_file_path):
            with open(password_file_path, 'r') as password_file:
                for line in password_file:
                    fields = [
                        field.strip() for field in line.rstrip().split(':')]
                    if len(fields) != 7:
                        self.logger.error(
                            f'The user {fields} does not have 7 fields.')
                        continue
                    user_username = fields[0].strip()
                    if not user_username:
                        self.logger.error(
                            f'The user {fields} is missing a username.')
                        continue
                    try:
                        user_id = int(fields[2].strip())
                        if user_id < 0:
                            raise ValueError(
                                f'The user_id {user_id} is invalid.')
                    except (TypeError, ValueError):
                        self.logger.error(
                            f'The user {fields} has an invalid user ID: '
                            f'{user_id}.')
                        continue
                    user_data[user_username] = user_id
        return user_data

    @staticmethod
    def get_user_project_data():
        """Return a list of lists where each entry corresponds to a
        single user from the user project worksheet.

        Parameters:
            - None

        Returns:
            - List of lists

        Raises:
            - Exception, if any errors occur
        """
        worksheet = get_gspread_worksheet(
            settings.GOOGLE_OAUTH2_KEY_FILE, USER_SPREADSHEET_ID,
            USER_PROJECT_SPREADSHEET_TAB)
        row_start = USER_PROJECT_SPREADSHEET_ROW_START
        row_end = len(worksheet.col_values(
            USER_PROJECT_SPREADSHEET_COLS['USERNAME']))
        col_start = 1
        col_end = USER_PROJECT_SPREADSHEET_COLS['PROJECTS']
        return get_gspread_worksheet_data(
            worksheet, row_start, row_end, col_start, col_end)

    def get_valid_projects(self, project_data):
        """Return the subset of the given projects that have valid
        fields in a list of dictionaries.

        Parameters:
            - project_data (list): a list of lists

        Returns:
            - List of lists

        Raises:
            - None
        """
        valid, invalid = [], []
        for row in project_data:
            name = row[PROJECT_SPREADSHEET_COLS['NAME'] - 1].strip()
            poc_names = row[PROJECT_SPREADSHEET_COLS['POC_NAMES'] - 1].strip()
            poc_emails = row[
                PROJECT_SPREADSHEET_COLS['POC_EMAILS'] - 1].strip()
            pi_names = row[PROJECT_SPREADSHEET_COLS['PI_NAMES'] - 1].strip()
            pi_emails = row[PROJECT_SPREADSHEET_COLS['PI_EMAILS'] - 1].strip()
            row_dict = {
                'name': name,
                'poc_names': [],
                'poc_emails': [],
                'pi_names': [],
                'pi_emails': [],
            }

            if not name or len(name) < 3 or not name.startswith(
                    tuple(PROJECT_PREFIXES)):
                invalid.append(row_dict)
                continue

            poc_names = [poc_name.strip() for poc_name in poc_names.split(',')]
            if not poc_names:
                invalid.append(row_dict)
                continue
            poc_names_valid = True
            for full_name in poc_names:
                if not self.is_full_name_valid(full_name):
                    poc_names_valid = False
                    break
            if not poc_names_valid:
                invalid.append(row_dict)
                continue
            row_dict['poc_names'] = poc_names

            poc_emails = [
                poc_email.strip() for poc_email in poc_emails.split(',')]
            if not poc_emails:
                invalid.append(row_dict)
                continue
            poc_emails_valid = True
            for email in poc_emails:
                if not self.is_email_address_valid(email):
                    poc_emails_valid = False
                    break
            if not poc_emails_valid:
                invalid.append(row_dict)
                continue
            row_dict['poc_emails'] = poc_emails

            pi_names = [pi_name.strip() for pi_name in pi_names.split(',')]
            if not pi_names:
                invalid.append(row_dict)
                continue
            pi_names_valid = True
            for full_name in pi_names:
                if not self.is_full_name_valid(full_name):
                    pi_names_valid = False
                    break
            if not pi_names_valid:
                invalid.append(row_dict)
                continue
            row_dict['pi_names'] = pi_names

            pi_emails = [pi_email.strip() for pi_email in pi_emails.split(',')]
            if not pi_emails:
                invalid.append(row_dict)
                continue
            pi_emails_valid = True
            for email in pi_emails:
                if not self.is_email_address_valid(email):
                    pi_emails_valid = False
                    break
            if not pi_emails_valid:
                invalid.append(row_dict)
                continue
            row_dict['pi_emails'] = pi_emails

            valid.append(row_dict)

        self.logger.info(f'Number of Valid Rows: {len(valid)}')
        self.logger.info(f'Number of Invalid Rows: {len(invalid)}')
        for invalid_row in invalid:
            self.logger.error(f'Invalid Row {invalid_row}.')

        return valid

    def get_valid_user_projects(self, user_project_data):
        """Return the subset of the given user project associations for
        which both the user and project exist.

        Parameters:
            - user_project_data (list): a list of lists

        Returns:
            - List of lists

        Raises:
            - None
        """
        valid, invalid = [], []
        for row in user_project_data:
            username = row[
                USER_PROJECT_SPREADSHEET_COLS['USERNAME'] - 1].strip()
            projects = row[
                USER_PROJECT_SPREADSHEET_COLS['PROJECTS'] - 1].strip()
            row_dict = {
                'username': username,
                'projects': projects
            }
            if not username:
                invalid.append(row_dict)
                continue
            try:
                User.objects.get(username=username)
            except User.DoesNotExist:
                invalid.append(row_dict)
                continue
            projects = [project.strip() for project in projects.split(',')]
            if not projects:
                invalid.append(row_dict)
                continue
            valid_projects = []
            for project_name in projects:
                try:
                    Project.objects.get(name=project_name)
                except Project.DoesNotExist:
                    self.logger.error(f'Invalid Project {project_name}.')
                else:
                    valid_projects.append(project_name)
            row_dict['projects'] = ','.join(valid_projects)
            valid.append(row_dict)
        self.logger.info(f'Number of Valid rows: {len(valid)}.')
        self.logger.info(f'Number of Invalid rows: {len(invalid)}.')
        for invalid_row in invalid:
            self.logger.error(f'Invalid row {invalid_row}.')
        return valid

    def get_valid_users(self, user_data):
        """Return the subset of the given users that have valid fields
        in a list of dictionaries.

        Parameters:
            - user_data (list): a list of lists

        Returns:
            - List of lists

        Raises:
            - None
        """
        user_ids = self.get_user_ids(PASSWD_FILE)
        valid, invalid = [], []
        for row in user_data:
            username = row[USER_SPREADSHEET_COLS['USERNAME'] - 1].strip()
            name = row[USER_SPREADSHEET_COLS['NAME'] - 1].strip()
            email = row[USER_SPREADSHEET_COLS['EMAIL'] - 1].strip()
            clusters = row[USER_SPREADSHEET_COLS['CLUSTERS'] - 1].strip()
            row_dict = {
                'username': username,
                'first_name': '',
                'middle_name': '',
                'last_name': '',
                'email': email,
                'clusters': clusters,
                'cluster_uid': None,
            }
            if not username:
                invalid.append(row_dict)
                continue
            if not name or not self.is_full_name_valid(name):
                invalid.append(row_dict)
                continue
            else:
                names = self.get_first_middle_last_names(name)
                row_dict['first_name'] = names['first']
                row_dict['middle_name'] = names['middle']
                row_dict['last_name'] = names['last']
            if not self.is_email_address_valid(email):
                invalid.append(row_dict)
                continue
            clusters = [cluster.strip() for cluster in clusters.split(',')]
            if not clusters:
                invalid.append(row_dict)
                continue
            clusters_valid = True
            for cluster in clusters:
                if cluster not in CLUSTERS:
                    clusters_valid = False
                    break
            if not clusters_valid:
                invalid.append(row_dict)
                continue
            valid.append(row_dict)
            if username in user_ids:
                row_dict['cluster_uid'] = user_ids[username]
        self.logger.info(f'Number of Valid Rows: {len(valid)}')
        self.logger.info(f'Number of Invalid Rows: {len(invalid)}')
        for invalid_row in invalid:
            self.logger.error(f'Invalid Row {invalid_row}.')
        return valid

    @staticmethod
    def is_email_address_valid(email):
        """Return whether or not the given email address is valid.

        Parameters:
            - email (str): an email address

        Returns:
            - Boolean

        Raises:
            - None
        """
        try:
            validate_email(email)
        except ValidationError:
            return False
        return True

    @staticmethod
    def is_full_name_valid(full_name):
        """Return whether or not the given full name is valid.

        Parameters:
            - full_name: a name that should have at least two components

        Returns:
            - Boolean

        Raises:
            - None
        """
        names = full_name.split()
        return len(names) >= 2
