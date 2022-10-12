from coldfront.config.base import SETTINGS_EXPORT
from coldfront.config.env import ENV

#------------------------------------------------------------------------------
# Advanced ColdFront configurations
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# General Center Information
#------------------------------------------------------------------------------
CENTER_NAME = ENV.str('CENTER_NAME', default='HPC Center')
CENTER_HELP_URL = ENV.str('CENTER_HELP_URL', default='')
CENTER_PROJECT_RENEWAL_HELP_URL = ENV.str('CENTER_PROJECT_RENEWAL_HELP_URL', default='')
CENTER_BASE_URL = ENV.str('CENTER_BASE_URL', default='')

#------------------------------------------------------------------------------
# Enable Project Review
#------------------------------------------------------------------------------
PROJECT_ENABLE_PROJECT_REVIEW = ENV.bool('PROJECT_ENABLE_PROJECT_REVIEW', default=True)

#------------------------------------------------------------------------------
# Allocation related
#------------------------------------------------------------------------------
ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT = ENV.bool('ALLOCATION_ENABLE_CHANGE_REQUESTS', default=True)
ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS = ENV.list('ALLOCATION_CHANGE_REQUEST_EXTENSION_DAYS', cast=int, default=[30, 60, 90])
ALLOCATION_ENABLE_ALLOCATION_RENEWAL = ENV.bool('ALLOCATION_ENABLE_ALLOCATION_RENEWAL', default=True)
ALLOCATION_FUNCS_ON_EXPIRE = ['coldfront.core.allocation.utils.test_allocation_function', ]

# This is in days
ALLOCATION_DEFAULT_ALLOCATION_LENGTH = ENV.int('ALLOCATION_DEFAULT_ALLOCATION_LENGTH', default=365)


#------------------------------------------------------------------------------
# Allow user to select account name for allocation
#------------------------------------------------------------------------------
ALLOCATION_ACCOUNT_ENABLED = ENV.bool('ALLOCATION_ACCOUNT_ENABLED', default=False)
ALLOCATION_ACCOUNT_MAPPING = ENV.dict('ALLOCATION_ACCOUNT_MAPPING', default={})

SETTINGS_EXPORT += [
    'ALLOCATION_ACCOUNT_ENABLED',
    'CENTER_HELP_URL'
]

ADMIN_COMMENTS_SHOW_EMPTY = ENV.bool('ADMIN_COMMENTS_SHOW_EMPTY', default=True)

#------------------------------------------------------------------------------
# List of Allocation Attributes to display on view page
#------------------------------------------------------------------------------
ALLOCATION_ATTRIBUTE_VIEW_LIST = ENV.list('ALLOCATION_ATTRIBUTE_VIEW_LIST', default=['slurm_account_name', 'freeipa_group', 'Cloud Account Name', ])

#------------------------------------------------------------------------------
# Enable invoice functionality
#------------------------------------------------------------------------------
INVOICE_ENABLED = ENV.bool('INVOICE_ENABLED', default=True)
# Override default 'Pending Payment' status
INVOICE_DEFAULT_STATUS = ENV.str('INVOICE_DEFAULT_STATUS', default='New')

#------------------------------------------------------------------------------
# Enable Open OnDemand integration
#------------------------------------------------------------------------------
ONDEMAND_URL = ENV.str('ONDEMAND_URL', default=None)

#------------------------------------------------------------------------------
# Default Strings. Override these in local_settings.py
#------------------------------------------------------------------------------
LOGIN_FAIL_MESSAGE = ENV.str('LOGIN_FAIL_MESSAGE', '')

EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL = """
You recently applied for renewal of your account, however, to date you have not entered any publication nor grant info in the ColdFront system. I am reluctant to approve your renewal without understanding why. If there are no relevant publications or grants yet, then please let me know. If there are, then I would appreciate it if you would take the time to enter the data (I have done it myself and it took about 15 minutes). We use this information to help make the case to the university for continued investment in our department and it is therefore important that faculty enter the data when appropriate. Please email xxx-helpexample.com if you need technical assistance.

As always, I am available to discuss any of this.

Best regards
Director


xxx@example.edu
Phone: (xxx) xxx-xxx
"""

ACCOUNT_CREATION_TEXT = '''University faculty can submit a help ticket to request an account.
Please see <a href="#">instructions on our website</a>. Staff, students, and external collaborators must
request an account through a university faculty member.
'''

#------------------------------------------------------------------------------
# Organization settings
#------------------------------------------------------------------------------

# --- Organization and User pages
# Whether or not to display Organizations for User on UserProfile page
# Accepts one of the following 3 case-insensitive string values:
# 'always' => always display
# 'never' => never display
# 'not-empty' => display only if user belongs to any organizations
# Any string not matching the above is treated as 'non-empty'
ORGANIZATION_USER_DISPLAY_MODE = ENV.str(
    'ORGANIZATION_USER_DISPLAY_MODE', 'not-empty').lower()
# Title to give for display of Organizations in user profile page
ORGANIZATION_USER_DISPLAY_TITLE = ENV.str(
    'ORGANIZATION_USER_DISPLAY_TITLE', 'Department(s), etc.')

# --- Organization and Project pages
# Whether or not to display Organizations for User on Project detail page
# Accepts one of the following 3 case-insensitive string values:
# 'always' => always display
# 'never' => never display
# 'not-empty' => display only if user belongs to any organizations
# Any string not matching the above is treated as 'non-empty'
ORGANIZATION_PROJECT_DISPLAY_MODE = ENV.str(
    'ORGANIZATION_PROJECT_DISPLAY_MODE', 'not-empty').lower()
# Title to give for display of Organizations in Project Detail page
ORGANIZATION_PROJECT_DISPLAY_TITLE = ENV.str(
    'ORGANIZATION_PROJECT_DISPLAY_TITLE', 'Department(s), etc.')
# Whether the ORganizations to which a Project is associated can be editted on
#the standard Project Update form; i.e. whether a PI can edit the Orgs for 
#their projects, Boolean
ORGANIZATION_PI_CAN_EDIT_FOR_PROJECT = ENV.bool(
    'ORGANIZATION_PI_CAN_EDIT_FOR_PROJECT', True)

# --- Integration between Organization and LDAP
# Should LDAP auth automatically populate Organizations for user
# (ignored unless PLUGIN_LDAP_AUTH is also True) (use 1/0 for env vars)
ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS = ENV.bool(
    'ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS', False)

# Name of attribute of ldap_user used for populating Organizations 
# for user (the attribute should return strings matching 
# directory_string in Directory2Organization table)
# PORG is for setting the Primary Organization, and ORG is
# for secondary Organizations
ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE = ENV.str(
    'ORGANIZATION_LDAP_USER_ORG_ATTRIBUTE', None)
ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE = ENV.str(
    'ORGANIZATION_LDAP_USER_PORG_ATTRIBUTE', None)

# Whether to create placeholder organizations (and assign to user)
# when encounter an unrecognized directory_string when updating
# user's organization list from LDAP, Boolean
ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS = ENV.bool(
    'ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS', False)
# Whether to delete organizations present for user but not showing
# up in LDAP when updating user's organization list from LDAP 
ORGANIZATION_LDAP_USER_DELETE_MISSING = ENV.bool(
    'ORGANIZATION_LDAP_USER_DELETE_MISSING', False)

