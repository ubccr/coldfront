from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

#------------------------------------------------------------------------------
# Enable XDMoD support
#------------------------------------------------------------------------------
INSTALLED_APPS += [
    'coldfront.plugins.xdmod',
]

XDMOD_API_URL = ENV.str('XDMOD_API_URL')

# --- Integration between Organization and XDMod hierarchy
#
# The maximum number of tiers to consider when generating XDMoD files
XDMOD_MAX_HIERARCHY_TIERS = ENV.int('XDMOD_MAX_HIERARCHY_TIERS', 3)

#           XDMoD and Allocations

# Boolean.  If set, the lowest tier in XDMod hierarchy will be allocation
# based.
XDMOD_ALLOCATION_IN_HIERARCHY = ENV.bool('XDMOD_ALLOCATION_IN_HIERARCHY', False)
#
# The label and info used in hierarchy.json for Allocation tier (if 
# XDMOD_ALLOCATION_IN_HIERARCHY is set)
XDMOD_ALLOCATION_HIERARCHY_LABEL = ENV.str(
        'XDMOD_ALLOCATION_HIERARCHY_LABEL', 'Allocation')
XDMOD_ALLOCATION_HIERARCHY_INFO = ENV.str(
        'XDMOD_ALLOCATION_HIERARCHY_INFO', 'Allocation')
# If Allocations are in the hierarchy, the following variables are used to
# generate the codes and names used in the XDMod hierarchy.csv and similar
# files.  See the xdmod_hier_code_for_allocation() method in
# coldfront.plugins.xdmod.utils for more detail.
#
# Attributes to use for the code and name of Allocation level entry in hierarchy
# See coldfront.plugins.xdmod.utils.xdmod_heir_code_for_allocation for more
# detail
XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME = ENV.str(
        'XDMOD_ALLOCATION_HIERARCHY_CODE_ATTRIBUTE_NAME', 'xdmod_alloc_code')
XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME = ENV.str(
        'XDMOD_ALLOCATION_HIERARCHY_NAME_ATTRIBUTE_NAME', 'xdmod_alloc_name')
# If the code and name are defaulted using the Slurm account name for the
# allocation, the following are prefixed/suffixed to that.
XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX = ENV.str(
    'XDMOD_ALLOCATION_HIERARCHY_CODE_PREFIX', '')
XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX = ENV.str(
    'XDMOD_ALLOCATION_HIERARCHY_CODE_SUFFIX', '')

#           XDMoD and Projects

# Boolean.  If set, the lowest or second lowest (if Allocations are in
# the hierarchy) tier of the XDMod hierarchy will be the Project level.
XDMOD_PROJECT_IN_HIERARCHY = ENV.bool('XDMOD_PROJECT_IN_HIERARCHY', False)
#
# The label and info used in hierarchy.json for Project tier (if 
# XDMOD_PROJECT_IN_HIERARCHY is set)
XDMOD_PROJECT_HIERARCHY_LABEL = ENV.str(
        'XDMOD_PROJECT_HIERARCHY_LABEL', 'Project')
XDMOD_PROJECT_HIERARCHY_INFO = ENV.str(
        'XDMOD_PROJECT_HIERARCHY_INFO', 'Project')
# If Projects are in the hierarchy, the following variables are used to
# generate the codes and names used in the XDMod hierarchy.csv and similar
# files.  See the xdmod_hier_code_for_project() method in
# coldfront.plugins.xdmod.utils for more detail.
#
# This value determines the general algorithm to use for generating the code
# and name for Project level entities in the XDMod hierarchy.  It takes one
# or more string values (multiple values should be delimitted by commas), 
# trying each one in left to right order until a value is obtained.  Recognized
# values are:
#   pi_username: the basename will be the username of the Project's PI
#   -slurm_account_name: The basename will be found by taking the Slurm account
#       names (using SLURM_ACCOUNT_ATTRIBUTE_NAME) of all Allocations under the
#       project, and then using the first in lexical order.
#   +slurm_account_name: Like -slurm_account_name, but take the last in lexical
#       order
#   title: The Project's title will be used as the basename
#   attribute: This will search all Allocations belonging to the Project to see
#       if any have an AllocationAttribute of type named by the value of
#       XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME, and if so use the value
#       of that attribute as the code (*not* basename for code).  If multiple
#       allocations have such an attribute set, the allocation with the lowest
#       pk is used (in order to be deterministic; you probably should ensure
#       all allocations of a project have the same value in this case)
#       If no allocation found with that attribute, fall to the next mode in
#       the list
XDMOD_PROJECT_HIERARCHY_CODE_MODE = ENV.str(
    'XDMOD_PROJECT_HIERARCHY_CODE_MODE', 'pi_username').lower()
# This variable gives the name of the AllocationAttributeType to use for
# the 'attribute' setting of XDMOD_PROJECT_HIERARCHY_CODE_MODE.
XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME = ENV.str(
    'XDMOD_PROJECT_HIERARCHY_CODE_ATTRIBUTE_NAME', 'xdmod_project_code')
# Unless the code was obtained from the AllocationAttribute, it will have
# the following prefixed/suffixed to it
XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX = ENV.str(
    'XDMOD_PROJECT_HIERARCHY_CODE_SUFFIX', '')
XDMOD_PROJECT_HIERARCHY_CODE_PREFIX = ENV.str(
    'XDMOD_PROJECT_HIERARCHY_CODE_PREFIX', '')

#           XDMoD and Users

# These controls what is produced for the first_name and last_name fields for
# Users when generating the XDMoD names.csv file.  These strings are processed
# by the Python str.format() method, with the arguments fname, lname, username,
# and email being passed (with values from the User's first_name, last_name,
# username, and email fields, respectively).
XDMOD_NAMES_CSV_USER_FNAME_FORMAT = ENV.str(
    'XDMOD_NAMES_CSV_USER_FNAME_FORMAT', '{fname}')
XDMOD_NAMES_CSV_USER_LNAME_FORMAT = ENV.str(
    'XDMOD_NAMES_CSV_USER_LNAME_FORMAT', '{lname}')

