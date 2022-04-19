import sys
import os
from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.test import TestCase

import coldfront.plugins.xdmod.utils as xdmod
import coldfront.plugins.slurm.utils as slurm
import coldfront.core.utils as utils
import coldfront.core.organization.models as organization
import coldfront.core.organization.signals as orgsignals

# Both resource.models and allocation.models have a class AttributeType
# So import each with different name
from coldfront.core.resource.models import AttributeType as RAttributeType
from coldfront.core.allocation.models import AttributeType as AAttributeType

from coldfront.core.allocation.models import (
        Allocation,
        AllocationAttribute,
        AllocationAttributeType,
        AllocationStatusChoice,
        AllocationUser,
        AllocationUserStatusChoice,
    )
from coldfront.core.field_of_science.models import (
        FieldOfScience,
        )
from coldfront.core.organization.models import (
        Organization,
        OrganizationLevel, 
        OrganizationProject,
        OrganizationUser,
        Directory2Organization,
        )
from coldfront.core.project.models import (
        Project,
        ProjectStatusChoice,
        ProjectUser,
        ProjectUserRoleChoice,
        ProjectUserStatusChoice,
        )
from coldfront.core.resource.models import (
        Resource,
        ResourceAttribute,
        ResourceAttributeType,
        ResourceType,
    )
from coldfront.core.user.models import (
        UserProfile,
        )

from django.contrib.auth.models import (
        User,
        )
                                        

#-------------------------------------------------------------------
#                   GLOBALS
#-------------------------------------------------------------------

DEFAULT_ATTRIBNAME_FOR_CACHED_VARS = 'coldfront_config_var_cache'
# Used in defaulting Users
DEFAULT_EMAIL_DOMAIN = 'example.com'
                                        
DEFAULT_FIXTURE_NAME='organization_test_data.json'
DEFAULT_FIXTURE_DIR='./coldfront/coldfront/core/utils/fixtures'

#-------------------------------------------------------------------
#                   Classes
#-------------------------------------------------------------------

class ConfigChangingTestCase(TestCase):
    """For TestCases which need to change ColdFront config vars.

    This is an abstract base class, inheriting from Django TestCase
    for TestCases which need to temporarily modify Coldfront config
    variables.

    We provide a pair of helper methods, on of which will 
    cache the old value and set to a new value, and the other will
    restore the old value.  The values are cached in an instance
    variable (dict valued) of the ConfigChangingTestCase instance
    (named using the 'attribname_for_cached_vars' class variable
    for the instance variable name).

    """

    # Class variable specifying the name of the instance variable
    # holding the cache
    attribname_for_cached_vars=DEFAULT_ATTRIBNAME_FOR_CACHED_VARS

    # Helper functions
    def get_coldfront_config_cache(self):
        """Returns the coldfront config cache dictionary.

        Will create an empty dictionary if needed.
        """
        attribname = ConfigChangingTestCase.attribname_for_cached_vars
        if not hasattr(self, attribname):
            setattr(self, attribname, {})
        cache = getattr(self, attribname)
        return cache
    
    def get_coldfront_package_from_string(self, pkgname):
        """Returns the ColdFront package from a string.

        Recognized strings are:
            organization: Returns the package for coldfront.core.organization.models
            orgsignals: Returns the package for coldfront.core.organization.signals
            slurm: Returns the package for coldfront.plugins.slurm.utils
            slurm: Returns the package for coldfront.plugins.slurm.utils
            xdmod: Returns the package for coldfront.plugins.xdmod.utils
        Any other string will raise a ValueError
        """
        pkgmapping = {
                'organization': organization,
                'orgsignals': orgsignals,
                'slurm': slurm,
                'xdmod': xdmod,
            }
        if pkgname in pkgmapping:
            return pkgmapping[pkgname]
        else:
            tmp = ', '.join(pkgmapping.keys())
            raise ValueError('Expecting pkgname to be one of {}'.format(tmp))
        return

    def set_and_cache_coldfront_config_variable(self, pkgname, varname, new):
        """Sets and caches a config variable from ColdFront.

        pkgname should be a string for the package the config variable
        is from.  See get_coldfront_package_from_string for list of
        allowed values.

        varname should be string with the name of the variable,
        e.g. SLURM_CLUSTER_ATTRIBUTE_NAME

        new should be the value to set the variable to.
        Return value is the previous value of the variable
        """

        # Get our package and ensure varname is found in it
        pkg = self.get_coldfront_package_from_string(pkgname)
        if not hasattr(pkg, varname):
            raise RuntimeError('Variable {} appears not to be in {}'.format(
                varname, pkgname))
        # And get the current value of the variable
        oldval = getattr(pkg,varname)

        # Get our cache
        main_cache = self.get_coldfront_config_cache()
        if pkgname in main_cache:
            pkg_cache = main_cache[pkgname]
        else:
            # Not found, create empty dict
            pkg_cache = {}
            main_cache[pkgname] = pkg_cache

        # Ensure we have not already cached a value for it
        if varname in pkg_cache:
            # We already have a value cached for varname
            # We only allow this if the current and cached values
            # are the same
            olderval = pkg_cache[varname]
            if olderval != oldval:
                # Values do not match --- error
                raise RuntimeError('Already have a cached version of {} '
                    'with value {}, cannot cache'.format(
                    varname))
        else:
            # Cache the current value
            pkg_cache[varname] = oldval

        # And set to new value
        setattr(pkg, varname, new)
        return oldval

    def restore_cached_coldfront_config_variable(self, pkgname, varname):
        """Restores a coldfront config variable from the cache.
        
        Restores a coldfront config variable as cached by
        set_and_cache_coldfront_config_variable

        pkgname should be a string for the package the config variable
        is from.  See get_coldfront_package_from_string for list of
        allowed values.

        varname should be string with the name of the variable

        We will raise a RuntimeError if variable was not previously
        cached.

        We return the cached value of the variable (as well as setting
        the variable back to the cached value and deleting the cache entry)
        """
        # Get our package
        pkg = self.get_coldfront_package_from_string(pkgname)

        # Get our cache
        main_cache = self.get_coldfront_config_cache()
        if pkgname in main_cache:
            pkg_cache = main_cache[pkgname]
        else:
            raise RuntimeError('Attempt to restore var {} in pkg {} '
                'from the cache, but not vars for pkg are cached'.format(
                    varname, pkgname))

        if varname in pkg_cache:
            # Restore cached value
            oldval = pkg_cache[varname]
            setattr(pkg, varname, oldval)
            del pkg_cache[varname]
        else:
            raise RuntimeError('Attempt to restore var {} in pkg {} '
                'from cache but no cached value found'.format(
                    varname, pkgname))
        return oldval

    def set_and_cache_coldfront_config_variables(self, varhash):
        """Calls set_and_cache_coldfront_config_variable for all vars in dict.

        This method will set a bunch of ColdFront configuration variables for
        different packages to new values, caching the old values for later
        restoration.

        The dictionary varhash should have keys representing ColdFront
        packages, e.g. slurm, xdmod.  See get_coldfront_package_from_string
        for list of allowed values.

        The value for each key is again a dictionary, this time keyed on the
        name of the variable to cache and set.  The value for the key is
        the new value to set the variable to.
        """
        for pkgname, pkghash in varhash.items():
            for varname, newval in pkghash.items():
                self.set_and_cache_coldfront_config_variable(
                        pkgname, varname, newval)
        return

    def restore_cached_coldfront_config_variables(self, varhash):
        """Calls restore_cached_coldfront_config_variable for all vars in varhash.

        This will restore the values for a bunch of ColdFront configuration
        variables from the values in the cache.  I.e., it reverts the action
        of set_and_cache_coldfront_config_variable(s).

        The dictionary varhash has the same format as for the method
        set_and_cache_coldfront_config_variables, although for this method
        the actual values in the inner hash are ignored.
        """
        for pkgname, pkghash in varhash.items():
            for varname in pkghash:
                self.restore_cached_coldfront_config_variable(
                        pkgname, varname)
        return
#end: class ConfigChangingTestCase(TestCase):



class TestFixtureBuilderCommand(BaseCommand):
    """Base class for commands to build fixtures for tests.
    """

    help = """Setup test data and make fixtures.

    This command will generate test data in the database and
    optionally generate a fixture with that data for testing
    purposes.

    Arguments are:
        --fixture: If present, a fixture will be generated.  If
            this flag is given and --outfile is not, the filename
            for the fixture will be defaulted.
        --outfile: The name of the fixture file.  If this flag is
            given and --fixture was not, --fixture will be assumed.
        --directory: The directory in which to store the fixture
            file if being generated.  Defaults to the fixtures
            subdir of coldfront.core.utils
        --force: If this flag is given, will operate in force mode.
            This allows the clobbering of existing fixture files.
        --initialize: If this flag is given, before generating data
            this script will run 'initial_setup' on the database.

    For best results, it is recommended to start with an empty 
    database and use the initialize flag.  Otherwise, the newly generated
    data will be added to the existing data, and may update/overwrite
    existing data.
    """

    # The default name of the fixture
    default_fixture_name = 'test_fixture'

    def add_arguments(self, parser):
        """This defines arguments related to creating fixtures, etc.
        """
        parser.add_argument('--fixture', 
                help='Create a fixture',
                action='store_true',
                default=None)
        parser.add_argument('--outfile', '--file', '-f',
                help='Specify name to use for the fixture.  Implies --fixture if given; '
                    'Defaults to {} if --fixture given'.format(self.default_fixture_name),
                action='store',
                default=None)
        parser.add_argument('--directory','--dir', '-d',
                help='Directory in which to store fixtures.  Defaults to the '
                    '"fixtures" subdirectory under coldfront.core.utils.',
                action='store',
                default=None)
        parser.add_argument('--initialize', '--init', '--initial_setup', 
                help='If set, run "initial_setup" on DB before generating data',
                action='store_true')
        parser.add_argument('--force', '-F',
                help='FORCE flag.  If set, allows clobbering of an '
                    'existing fixture file',
                action='store_true')
        parser.add_argument('--nohistorical', '--nohistory',
                help='If set, exclude "historical" data from fixture',
                action='store_true')
        return

    def handle(self, *args, **options):
        """This does the basic handling of a fixture generating command.

        Subclasses are expected/required to override the create_data
        method.  
        """
        outfile = options['outfile']
        fixture = options['fixture']
        fixtures_dir = options['directory']
        initialize = options['initialize']
        nohistorical = options['nohistorical']
        FORCE = options['force']

        # If outfile was set, then --fixture is implied
        if outfile is not None:
            # Outfile was given, this implies fixture
            if fixture is None:
                fixture = True
            elif not fixture:
                raise CommandError('--outfile given but fixture set to false, not allowed')

        if fixture:
            fixture_path = self.get_fixture_path(
                    fixture_name=outfile,
                    fixtures_path= fixtures_dir,
                    )
            if os.path.isfile(fixture_path):
                if not FORCE:
                    raise CommandError('Fixture file {} already exists, '
                            'refusing to clobber w/out force flag.'.format(
                                fixture_path))
                #end: if not FORCE
            #end: if os.path.isfile
        #end: if fixture
        
        if initialize:
            self.run_initial_setup()

        # Create data
        self.create_data(options)

        if fixture:
            self.generate_fixture(
                    fixture_path=fixture_path,
                    nohistorical=nohistorical,
                    )
        return

    def generate_fixture(self, fixture_path, extra_arguments=None, nohistorical=False):
        """
        Generates a fixture, i.e. calls dumpdata command with the
        appropriate arguments.
        If extra_args is given, it should be a dict whose arguments
        will be passed to dumpdata.  Unless overridden by extra_args,
        we will pass the following arguments:
            format=json
            indent=2
            exclude = ['publication.PublicationSource' ]
        We will always (overriding extra_args if necessary) add
            output = fixture_path
        """
        if extra_arguments is None:
            extra_arguments = {}
        args = dict(extra_arguments)
        args['output'] = fixture_path

        if 'format' not in args:
            args['format'] = 'json'
        if 'indent' not in args:
            args['indent'] = 2
        if 'exclude' not in args:
            args['exclude'] = [ 'publication.PublicationSource' ]
        if nohistorical:
            extra_excludes = [
                    "allocation.historicalallocation",
                    "allocation.historicalallocationattribute",
                    "allocation.historicalallocationattributetype",
                    "allocation.historicalallocationuser",
                    "project.historicalproject",
                    "project.historicalprojectuser",
                    "resource.historicalresource",
                    "resource.historicalresourceattribute",
                    "resource.historicalresourceattributetype",
                    "resource.historicalresourcetype",
                ]
            args['exclude'].extend(extra_excludes)

        call_command(
                "dumpdata", 
                **args
            )
        return

    def run_initial_setup(self,extra_arguments=None):
        """Runs initial_setup on the DB
        """
        if extra_arguments is None:
            extra_arguments = {}
        args = dict(extra_arguments)

        call_command(
                "initial_setup", 
                **args
            )
        return

    def create_data(self, options):
            """Create the required data structure for this fixture, etc.

            This method *must* be overridden in all subclasses.
            """
            raise NotImplementedError('Subclasses of TestFixtureBuilderCommand '
                '*must* override the "create_data" method.')
            return

    def default_fixture_directory(self):
        """This returns the default directory in which to put the fixture.

        This base class defaults to the "fixtures" directory under
        coldfront.core.utils.
        """
        utils_path = utils.__path__
        utils_path = utils_path[0]
        fixtures_path = os.path.join(utils_path, 'fixtures')
        if not os.path.isdir(fixtures_path):
            os.mkdir(fixtures_path)
        return fixtures_path

    def get_fixture_path(self, fixture_name=None, fixtures_path=None):
        """Returns the full path to the fixture file.
        """
        if fixture_name is None:
            fixture_name = self.default_fixture_name
        if fixtures_path is None:
            fixtures_path = self.default_fixture_directory()

        fixture_path = os.path.join(fixtures_path, fixture_name)
        return fixture_path

#End: class TestFixtureBuilderCommand(BaseCommand):

#-------------------------------------------------------------------
#                  Utility functions
#-------------------------------------------------------------------

def verbose_msg(verbosity, message, minverbosity=1, indent=0):
    """Print message if verbosity > minverbosity.

    Minverbosity is the minimum verbosity level for which the 
    verbose message should be displayed.

    Verbosity can be given as an integer or as a dictionary with a
    key 'verbosity' which refers to an integer value (so that one can
    provide the 'options' parameter from a command.)

    If verbosity > minverbosity, the message is printed.  It will be
    prefixed with '[VERBOSE]' if minverbosity==1, or with
    '[VERBOSE:n]' if minverbosity=n > 1,

    The message will be indented by indent additional spaces after 
    the [VERBOSE]
    """
    if verbosity is None:
        # Treat None as verbosity=0
        verbosity = 0
    elif isinstance(verbosity, dict):
        if 'verbosity' in verbosity:
            verbosity = verbosity['verbosity']
        else:
            # If no verbosity key, treat as verbosity=0
            verbosity = 0

    if minverbosity > verbosity:
        # Verbosity is less than minimum verbosity
        return

    label = 'DEBUG'
    if minverbosity > 1:
        label = 'DEBUG:{}'.format(minverbosity)
    spaces = ' ' * indent

    text = '[{}] {}{}\n'.format(label, spaces, message.rstrip())
    sys.stderr.write(text)
    return

def create_organization_levels_from_dictlist(dlist, verbosity=None):
    """Calls create_or_update_organization_level_by_name for each dict in dlist.

    The optional parameter verbosity controls how much information if 
    printed out.  It can take any form acceptable to verbose_msg.
    Typically, we display
        At minverbosity 1: message that this function entered
        At minverbosity 2: message for every OrgLevel created/updated
        At minverbosity 3: details on updated OrgLevels, and on OrgLevels
            which did not get created/updated.
    """
    verbose_msg(verbosity, 'Creating OrganizationLevels...')
    for rec in dlist:
        if 'name' in rec:
            name = rec['name']
        else:
            raise ValueError('List elements must have a key named "name"')
        if 'level' in rec:
            level = rec['level']
        else:
            raise ValueError('List elements must have a key named "level"')
        if 'parent' in rec:
            parent = rec['parent']
        else:
            parent = None
        if 'export_to_xdmod' in rec:
            export_to_xdmod = rec['export_to_xdmod']
        else:
            export_to_xdmod = True
        
        obj, created, changes = \
                OrganizationLevel.create_or_update_organization_level_by_name(
                    name=name,
                    level=level,
                    parent=parent,
                    export_to_xdmod=export_to_xdmod,
                )
        if created:
            verbose_msg(verbosity, 'Created OrganizationLevel {}'.format(
                obj.name), 2, indent=4)
        elif changes:
            verbose_msg(verbosity, 'Updated OrganizationLevel '
                '{}'.format(obj.name), 2, indent=4)
            for change in changes:
                for fld, rec in changes.items():
                    verbose_msg(verbosity, 'Field {}: {} => {}'.format(
                        fld, rec['old'], rec['new']), 3, indent=8)
        else:
            verbose_msg(verbosity, 'OrganizationLevel {} exists, no '
                    'changes needed.'.format(obj.name), 3, indent=4)
    #end for rec
    return

def create_organizations_from_dictlist(dlist, verbosity=None):
    """Calls create_or_update_organization_by_code_parent for each dict in dlist

    The optional parameter verbosity controls how much information if 
    printed out.  It can take any form acceptable to verbose_msg.
    Typically, we display
        At minverbosity 1: message that this function entered
        At minverbosity 2: message for every OrgLevel created/updated
        At minverbosity 3: details on updated OrgLevels, and on OrgLevels
            which did not get created/updated.
    """
    verbose_msg(verbosity, 'Creating Organizations...')
    for rec in dlist:
        if 'code' in rec:
            code = rec['code']
        else:
            raise ValueError('Elements of list must have a key named "code"')
        if 'parent' in rec:
            parent = rec['parent']
        else:
            parent = None
        if 'organization_level' in rec:
            organization_level = rec['organization_level']
        else:
            raise ValueError('Elements of list must have a key named "organization_level"')
        if 'shortname' in rec:
            shortname = rec['shortname']
        else:
            shortname = code
        if 'longname' in rec:
            longname = rec['longname']
        else:
            longname = code
        if 'is_selectable_for_user' in rec:
            is_selectable_for_user = rec['is_selectable_for_user']
        else:
            is_selectable_for_user = True
        if 'is_selectable_for_project' in rec:
            is_selectable_for_project = rec['is_selectable_for_project']
        else:
            is_selectable_for_project = True

        obj, created, changes = \
                Organization.create_or_update_organization_by_parent_code(
                        code=code,
                        organization_level=organization_level,
                        shortname=shortname,
                        longname=longname,
                        parent=parent,
                        is_selectable_for_user=is_selectable_for_user,
                        is_selectable_for_project=is_selectable_for_project,
                    )
        if created:
            verbose_msg(verbosity, 'Created Organization {}'.format(
                obj.fullcode()), 2, indent=4)
        elif changes:
            verbose_msg(verbosity, 'Updated Organization '
                '{}'.format(obj.fullcode()), 2, indent=4)
            for change in changes:
                for fld, rec in changes.items():
                    verbose_msg(verbosity, 'Field {}: {} => {}'.format(
                        fld, rec['old'], rec['new']), 3, indent=8)
        else:
            verbose_msg(verbosity, '    Organization {} exists, no '
                    'changes needed.'.format(obj.fullcode()), 3, indent=4)

        # Add/update Directory2Organizations
        if 'directory2organization' in rec:
            dirstrs = rec['directory2organization']
            for dirstr in dirstrs:
                _, created, tmpchanges = \
                        Directory2Organization.create_or_update_by_directory_string(
                            directory_string=dirstr, 
                            organization=obj)
                if created:
                    verbose_msg(verbosity, 'Dir2Org string "{}" added'.format(
                        dirstr), 2, indent=4)
            #end: for dirstr
        #end if 'directory2organization' in rec
    #end for rec
    return

def create_or_update_user_by_username(fields,
        default_email_domain=DEFAULT_EMAIL_DOMAIN):
    """Create an User + UserProfile from data in fields, if needed
    
    Checks to see if an User with given username already exists.  If 
    not, a new User is created.  If it exists, we update the User 
    object according to fields.

    This method also will update the User's password if requested, and
    create and/or update the UserProfile object as needed.

    The dictionary odict can contain the following fields
        name: Fullname of user, only used for defaulting first_name,
            last_name
        first_name: First name of user. If omitted and name was given,
            it will be defaulted to everything before the last space
            in name.
        last_name: Last name of user.  If omitted and name was given,
            it will be defaulted to everything after the last space 
            in name.
        username: Username. Defaults to first letter of first_name
            and last_name, all lowercased.
        email: Email of user.  Defaults to username + @ + 
            default_email_domain class attribute
        is_superuser: Boolean, if user is a superuser.  Defaults to False
        is_staff: Boolean, if user is staff.  Defaults to False
        password: Optional.  If provided, set password of user to this.
        is_active: Boolean,  Defaults to True
        date_joined: Defaults to current date
        is_pi: Boolean.  Defaults to False
        organizations: This should be a list of dicts with keys
            "organization" and "is_primary", or an instance of Organization
            or a fullcode for an Organization.  The value of the "organization"
            key should be an Organization instance or fullcode.  These 
            organizations will become the organizations associated with
            the User; any previously defined Organizations not found in
            this list will be deleted.
            If the first entry in the list is not a dict or is missing the
            is_primary key, we will default is_primary to true for that
            entry.  For all other entries, is_primary defaults to false.
        add_organizations: Same format as organizations, but previously
            defined Organizations for the User not in this list will not
            be deleted (although may get demoted to "secondary" orgs if
            an element in this list is flagged as is_primary).
        del_organizations: Same format as organizations, except the
            is_primary key, if present, is completely ignored.  These
            organizations will be removed from the User.

    The organization keys are processed in the following order:
        'organizations', 'add_organizations', 'del_organizations'

    Returns a tuple (user, created, changes, uprof, created2, changes2)
    where
        user is the new or previously-existing OrganizationLevel
        created is a boolean which is true if a new OrgLevel was created
        changes is a (possibly empty) indicating keyed on fields which
            were updated (if existing object updated), the value is 
            a dictionary with keys 'old' and 'new' giving the old and new
            values.
        uprof, created2, and changes2 are similar, but for the UserProfile
            instance.
    """
    args = {}
    created = False
    changes = {}
    created2 = False
    changes2 = {}

    # Get username, defaulting if needed
    name = None
    if 'name' in fields:
        name = fields['name']

    first_name = None
    if 'first_name' in fields:
        first_name = fields['first_name']
    else:
        if name is not None:
            first_name = name.rsplit(' ',1)[0]

    last_name = None
    if 'last_name' in fields:
        last_name = fields['last_name']
    else:
        if name is not None:
            last_name = name.rsplit(' ',1)[-1]

    username = None
    if 'username' in fields:
        username = fields['username']
    else:
        if first_name is not None and last_name is not None:
            username = first_name[0].lower() + last_name.lower()
            username = username.strip()

    # See if User with given username exists
    qset = User.objects.filter(username=username)
    if qset:
        #User exists, check if anything needs updating
        user = qset[0]
        args = {}
        args['username'] = username
        fnames = [
                'first_name',
                'last_name',
                'email',
                'is_superuser',
                'is_staff',
                'is_active',
                'date_joined',
                ]
        for fld in fnames:
            if fld in fields:
                new = fields[fld]
                old = getattr(user, fld)
                if old != new:
                    changes[fld] = { 'old':old, 'new':new }
                    setattr(user, fld, new)
                    user.save()
    else: #if qset
        # Need to create a new User
        args['username'] = username
        args['first_name'] = first_name
        args['last_name'] = last_name
        if 'email' in fields:
            args['email'] = fields['email']
        else:
            args['email'] = '{}@{}'.format(
                    username, default_email_domain)
        
        # These default to False
        fnames = [ 'is_superuser', 'is_staff' ]
        for fld in fnames:
            if fld in fields:
                args[fld] = fields[fld]
            else:
                args[fld] = False

        # These default to True
        fnames = [ 'is_active' ]
        for fld in fnames:
            if fld in fields:
                args[fld] = fields[fld]
            else:
                args[fld] = True

        # These default to the current date
        fnames = [ 'date_joined' ]
        for fld in fnames:
            if fld in fields:
                args[fld] = fields[fld]
            else:
                args[fld] = date.today()

        user = User.objects.create(**args)
    #end: if qset

    # Change password if requested
    if 'password' in fields:
        old = user.password
        user.set_password(fields['password'])
        new = user.password
        if old != new:
            changes['password'] = { 
                    'old': 'UNKNOWN',
                    'new': fields['password'],
                }
            user.save()

    # Check if UserProfile exists
    qset = UserProfile.objects.filter(user=user)
    if qset:
        # UserProfile already exists, update if needed
        uprof = qset[0]
        if 'is_pi' in fields:
            old = uprof.is_pi
            new = fields['is_pi']
            if old != new:
                uprof.is_pi = new
                uprof.save()
                changes2['is_pi'] = { 'old':old, 'new':new }
    else: #if qset:
        # Need to create new UserProfile object
        args = {}
        args['user'] = user
        if 'is_pi' in fields:
            args['is_pi'] = fields['is_pi']
        else:
            args['is_pi'] = False

        uprof = UserProfile.objects.create(**args)
        created2 = True
    #end: if qset

    # Process organizations
    if 'organizations' in fields:
        orgs = fields['organizations']
        tmpchanges = OrganizationUser.set_organizations_for_user(
                user=user,
                organization_list=orgs,
                delete=True,
                default_first_primary=True,
            )
        changes.update(tmpchanges)
    if 'add_organizations' in fields:
        orgs = fields['add_organizations']
        tmpchanges = OrganizationUser.set_organizations_for_user(
                user=user,
                organization_list=orgs,
                delete=False,
                default_first_primary=False,
            )
        changes.update(tmpchanges)
    if 'del_organizations' in fields:
        orgs = fields['del_organizations']
        tmpchagnes = OrganizationUser.delete_organizations_for_user(
                user=user,
                organization_list=orgs,
            )
        changes.update(tmpchanges)

    return user, created, changes, uprof, created2, changes2

def create_users_from_dictlist(dlist, verbosity=None):
    """Calls create_or_update_user_by_username for each dict in dlist

    This will create Users and UserProfiles from a list of dictionaries
    describing the User.

    The optional parameter verbosity controls how much information if 
    printed out.  It can take any form acceptable to verbose_msg.
    Typically, we display
        At minverbosity 1: message that this function entered
        At minverbosity 2: message for every OrgLevel created/updated
        At minverbosity 3: details on updated OrgLevels, and on OrgLevels
            which did not get created/updated.
    """
    verbose_msg(verbosity, 'Creating Users and UserProfiles...')
    for rec in dlist:
        user, created, changes, uprof, created2, changes2 = \
            create_or_update_user_by_username(rec)
        if created:
            verbose_msg(verbosity, 'Created User {}'.format(
                user.username), 2, indent=4)
        elif changes:
            verbose_msg(verbosity, 'Updated User '
                '{}'.format(user.username), 2, indent=4)
            for change in changes:
                for fld, rec in changes.items():
                    verbose_msg(verbosity, 'Field {}: {} => {}'.format(
                        fld, rec['old'], rec['new']), 3, indent=8)
        else:
            verbose_msg(verbosity, '    User {} exists, no '
                    'changes needed.'.format(user.username), 3, indent=4)
        if created2:
            verbose_msg(verbosity, 'Created UserProfile for {}'.format(
                user.username), 2, indent=4)
        elif changes2:
            for change in changes2:
                verbose_msg(verbosity, 'Updated UserProfile for '
                    '{}'.format(user.username), 2, indent=4)
                for fld, rec in changes2.items():
                    verbose_msg(verbosity, 'Field {}: {} => {}'.format(
                        fld, rec['old'], rec['new']), 3, indent=8)
        else:
            verbose_msg(verbosity, 'UserProfile for {} exists, no '
                    'changes needed.'.format(user.username), 3, indent=4)
    #end for rec
    return

def create_rattribute_type_by_name(fields):
    """Create an AttributeType for Resources by name, if needed.

    Returns a doublet (obj, created)
    where
        obj is the new or previously-existing AttributeType
        created is a boolean which is true if a new AttributeType was created
    """
    name = fields['name']
    obj, created = RAttributeType.objects.get_or_create(name=name)
    return obj, created

def create_rattributes_from_dictlist(dlist, verbosity=None):
    """Calls create_rattribute_type_by_name for each dict in dlist
    """
    verbose_msg(verbosity, 'Creating AttributeTypes (for Resources)...')
    for rec in dlist:
        obj, created = create_rattribute_type_by_name(rec)
        if created:
            verbose_msg(verbosity, 'Created (Resource) AttributeType {}'.format(
                obj), 2, indent=4)
        else:
            verbose_msg(verbosity, '(Resource) AttributeType {} exists, no '
                    'changes needed'.format(obj), 3, indent=4)
    return

def create_or_update_resourcetype_by_name(fields):
    """Create or update a ResourceType by name, as needed.

    Checks for existance of ResourceType with specified name.
    If it exists, update description if needed.  If not, create ResourceType.

    Fields can have fields:
        name: Name of ResourceType, required
        description: Desc of Resource, no default

    Returns a triplet (obj, created, changes)
    where
        obj is the new or previously-existing AttributeType
        created is a boolean which is true if a new AttributeType was created
        changes: For updated objects, this is dict keys on fields changed, which
            is dict with keys old and new for old nad new values
    """
    created = False
    changes = {}
    name = fields['name']
    qset = ResourceType.objects.filter(name=name)
    if qset:
        # We have a ResourceType with specified name
        obj = qset[0]
        if 'description' in fields:
            old = obj.description
            new = fields['description']
            if old != new:
                obj.description = new
                obj.save()
                changes['description'] = { 'old':old, 'new':new }
    else: #if qset
        created = True
        args['name'] = name
        if 'description' in fields:
            args['description'] = fields['description']
        obj = ResourceType.objects.create(**args)

    return obj, created

def create_resourcetypes_from_dictlist(dlist, verbosity=None):
    """Calls create_or_update_resourcetype_by_name for each dict in dlist
    """
    verbose_msg(verbosity, 'Creating ResourceTypes...')
    for rec in dlist:
        obj, created, changes = create_or_update_resourcetype_by_name(rec)
        if created:
            verbose_msg(verbosity, 'Created ResourceType {}'.format(
                obj), 2, indent=4)
        elif changes:
            verbose_msg(verbosity, 'Updated ResourceType '
                '{}'.format(obj), 2, indent=4)
            for change in changes:
                for fld, rec in changes.items():
                    verbose_msg(verbosity, 'Field {}: {} => {}'.format(
                        fld, rec['old'], rec['new']), 3, indent=8)
        else:
            verbose_msg(verbosity, 'ResourceType {} exists, no '
                    'changes needed.'.format(obj), 3, indent=4)
    return

def create_or_update_resourceattributetype_by_name(fields):
    """Create or update a ResourceAttributeType by name, as needed.

    Checks for existance of ResourceAttributeType with specified name.
    If it exists, update description if needed.  If not, create ResourceAttributeType.

    Fields can have fields:
        name: Name of ResourceAttributeType, required
        attribute_type: Name of (Resource) AttributeType
        is_required:
        is_unique_per_resource:
        is_value_unique:

    Returns a triplet (obj, created, changes)
    where
        obj is the new or previously-existing AttributeType
        created is a boolean which is true if a new AttributeType was created
        changes: For updated objects, this is dict keys on fields changed, which
            is dict with keys old and new for old nad new values
    """
    created = False
    changes = {}
    name = fields['name']

    qset = ResourceAttributeType.objects.filter(name=name)
    if qset:
        # We have a ResourceAttributeType with specified name
        obj = qset[0]
        if 'attribute_type' in fields:
            old = obj.attribute_type
            newname = fields['attribute_type']
            if newname is not None:
                new = RAttributeType.objects.get(name=newname)
            else:
                new = None
            if old != new:
                obj.attribute_type = new
                obj.save()
                changes['attribute_type'] = { 'old':old, 'new':new }
    else: #if qset
        created = True
        args['name'] = name
        if 'attribute_type' in fields:
            newname = fields['attribute_type']
            if newname is not None:
                new = RAttributeType.objects.get(name=newname)
            else:
                new = None
            args['attribute_type'] = new

        # These default in constructor
        fnames = [ 'is_required', 'is_unique_per_resource', 'is_value_unique' ]
        for fname in fnames:
            if fname in fields:
                args[fname] = fields[fname]

        obj = ResourceAttributeType.objects.create(**args)

    return obj, created, changes

def create_resourceattributetypes_from_dictlist(dlist, verbosity=None):
    """Calls create_or_update_resourceattributetype_by_name for each dict in dlist
    """
    verbose_msg(verbosity, 'Creating ResourceAttributeTypes...')
    for rec in dlist:
        obj, created, changes = create_or_update_resourceatributetype_by_name(rec)
        if created:
            verbose_msg(verbosity, 'Created ResourceAttributeType {}'.format(
                obj), 2, indent=4)
        elif changes:
            verbose_msg(verbosity, 'Updated ResourceAttributeType '
                '{}'.format(obj), 2, indent=4)
            for change in changes:
                for fld, rec in changes.items():
                    verbose_msg(verbosity, 'Field {}: {} => {}'.format(
                        fld, rec['old'], rec['new']), 3, indent=8)
        else:
            verbose_msg(verbosity, 'ResourceAttributeType {} exists, no '
                    'changes needed.'.format(obj), 3, indent=4)
    return

def create_or_update_resource_by_name(fields):
    """Create or update a Resource by name, as needed.

    Checks for existance of Resource with specified name.
    If it exists, update description if needed.  If not, create ResourceAttributeType.

    Fields can have fields:
        name: Name of Resource, required
        parent_resource: Name of parent Resource
        resource_type: Name of ResourceType
        is_available:
        is_public:
        is_allocatable:
        requires_payment:
        allowed_groups:
        allowed_users:
        linked_resources:
        resource_attributes: list of dictionaries with keys
            resource_attribute_type: Name of ResourceAttributeType
            value: value of ResourceAttribute

    Returns a triplet (obj, created, changes)
    where
        obj is the new or previously-existing AttributeType
        created is a boolean which is true if a new AttributeType was created
        changes: For updated objects, this is dict keys on fields changed, which
            is dict with keys old and new for old nad new values
    """
    created = False
    changes = {}
    name = fields['name']

    qset = Resource.objects.filter(name=name)
    if qset:
        # We have a Resource with specified name
        obj = qset[0]

        if 'parent_resource' in fields:
            pname = fields['parent_resource']
            if pname is None:
                parent = None
            else:
                parent = Resource.objects.get(name=pname)
            old = obj.parent_resource
            if old is not None:
                if parent is None or old != parent:
                    obj.parent_resource = parent
                    obj.save()
                    changes['parent_resource'] = { 'old':old, 'new':parent }
            else:
                if parent is not None:
                    obj.parent_resource = parent
                    obj.save()
                    changes['parent_resource'] = { 'old':old, 'new':parent }
        if 'linked_resources' in fields:
            lresrcs = set(fields['linked_resources'])
            old = obj.linked_resources
            tmpadded = []
            tmpremoved = []
            tmpold = []
            # Make linked_resources for obj match what we were given
            for lres in old:
                tmpold.append(lres.name)
                if lres.name in lresrcs:
                    # Linked resource in both, nothing to do
                    lresrcs.remove(lres.name)
                else:
                    # Existing linked resource not in list we were given, delete it
                    tmpremoved.append(lres.name)
                    obj.linked_resources.remove(lres)
            for lresname in lresrcs:
                lres = Resource.objects.get(name=lresname)
                obj.linked_resources.add(lres)
                tmpadded.append(lresname)
            tmp1 = ', +'.join(tmpadded)
            tmp2 = ', -'.join(tmpremoved)
            old = ', '.join(tmpold)
            new = '{}, {}'.format(tmp1, tmp2)
            changes['linked_resources'] = { 'old':old, 'new':new }

        if 'resource_type' in fields:
            rtname = fields['resource_type']
            if rtname is not None:
                rtype = ResourceType.objects.get(name=rtname)
            else:
                rtype = None
            old = obj.resource_type
            if old != rtype:
                obj.resource_type = rtype
                changes['resource_type'] = { 'old':old.name, 'new':rtname }

        # The remaining fields are simple values
        fnames = [ 'description', 'is_available', 'is_public', 
                'is_allocatable', 'requires_payment', ]
        for fld in fnames:
            old = getattr(obj, fld)
            new = fields[fld]
            if old != new:
                changes[fld] = { 'old':old, 'new':new }
                setattr(obj, fld, new)
                user.save()
    else: #if qset
        created = True
        args={}
        args['name'] = name

        if 'resource_type' in fields:
            rtname = fields['resource_type']
            if rtname is None:
                rtype = None
            else:
                rtype = ResourceType.objects.get(name=rtname)
            args['resource_type'] = rtype

        if 'parent_resource' in fields:
            newname = fields['parent_resource']
            if newname is not None:
                new = Resourcee.objects.get(name=newname)
            else:
                new = None
            args['parent_resource'] = new

        if 'linked_resources' in fields:
            tmp = fields['linked_resources']
            new = []
            if tmp is None:
                new = None
            else:
                for lresname in tmp:
                    lres = Resource.objects.get(name=lresname)
                    new.append(lres)
            args['linked_resources'] = tmp

        # These default in constructor
        fnames = [ 'description', 'is_available', 'is_public',
                'is_allocatable', 'requires_payment' ]
        for fname in fnames:
            if fname in fields:
                args[fname] = fields[fname]

        obj = Resource.objects.create(**args)
    #end: if qset

    # Update resource_attributes as needed
    if 'resource_attributes' in fields:
        ralist = fields['resource_attributes']
        for rarec in ralist:
            ratname = rarec['resource_attribute_type']
            ratype = ResourceAttributeType.objects.get(name=ratname)
            if 'value' in rarec:
                value = rarec['value']
            else: #if 'value' in rarec
                value = None
            qset = ResourceAttribute.objects.filter(
                    resource_attribute_type=ratype,
                    resource=obj,
                    )
            #end: if 'value' in rarec:
            if qset:
                # Already have this attribute, update value
                rattrib = qset[0]
                old = rattrib.value
                if old != value:
                    rattrib.value = value
                    rattrib.save()
                    changes['ResourceAttribute-{}'.format(ratname)] = {
                            'old':old, 'new':value }
            else: #if qset:
                rattrib = ResourceAttribute.objects.create(
                        resource=obj,
                        resource_attribute_type=ratype,
                        value=value,
                    )
                changes['ResourceAttribute-{}'.format(ratname)] = {
                        'old':None, 'new':value }
            #end: if qset:
    return obj, created, changes

def create_resources_from_dictlist(dlist, verbosity=None):
    """Calls create_or_update_resource_by_name for each dict in dlist
    """
    verbose_msg(verbosity, 'Creating Resources...')
    for rec in dlist:
        obj, created, changes = create_or_update_resource_by_name(rec)
        if created:
            verbose_msg(verbosity, 'Created Resource {}'.format(
                obj), 2, indent=4)
        elif changes:
            verbose_msg(verbosity, 'Updated Resource '
                '{}'.format(obj), 2, indent=4)
            for change in changes:
                for fld, rec in changes.items():
                    verbose_msg(verbosity, 'Field {}: {} => {}'.format(
                        fld, rec['old'], rec['new']), 3, indent=8)
        else:
            verbose_msg(verbosity, 'Resource {} exists, no '
                    'changes needed.'.format(obj), 3, indent=4)
    return

def create_or_update_resourceattribute_by_resource_type(fields):
    """Create or update a ResourceAttribute by resource and attribtype as needed.

    Checks for existance of ResourceAttribute with specified Resource and
    ResourceAttributeType.
    If it exists, update value if needed.  If not, create ResourceAttributeType.

    Fields can have fields:
        resource: Name of Resource, required
        resource_attribute_type: Name of ResourceAttributeType
        value: value of ResourceAttribute

    Returns a triplet (obj, created, changes)
    where
        obj is the new or previously-existing AttributeType
        created is a boolean which is true if a new AttributeType was created
        changes: For updated objects, this is dict keys on fields changed, which
            is dict with keys old and new for old nad new values
    """
    created = False
    changes = {}

    resname = fields['resource']
    if resname is None:
        resource = None
    else:
        resource = Resource.objects.get(name=resname)

    ratname = fields['resource_attribute_type']
    if ratname is None:
        ratype = None
    else:
        ratype = ResourceAttributeType.objects.get(name=ratname)

    qset = ResourceAttribute.objects.filter(
            resource_attribute_type=ratype, resource=resource)

    if qset:
        # Got a match
        obj = qset[0]

        if 'value' in fields:
            value = fields['value']
            old = obj.value
            if value is None:
                if old is not None:
                    obj.value = value
                    obj.save()
                    changes['value'] = { 'old':old, 'new':value }
            elif old is not None or old != value:
                obj.value = value
                obj.save()
                changes['value'] = { 'old':old, 'new':value }
    else: #if qset
        args = {}
        args['resource'] = resource
        args['resource_attribute_type'] = ratype
        if 'value' in fields:
            args['value'] = fields['value']
        obj = ResourceAttribute.objects.create(**args)

    return obj, created, changes

def create_resourceattributes_from_dictlist(dlist, verbosity=None):
    """Calls create_or_update_resourceattribute_by_resource_type for each dict in dlist
    """
    verbose_msg(verbosity, 'Creating ResourceAttributes...')
    for rec in dlist:
        obj, created, changes = create_or_update_resourceattribute_by_resource_type(rec)
        if created:
            verbose_msg(verbosity, 'Created ResourceAttribute {}'.format(
                obj), 2, indent=4)
        elif changes:
            verbose_msg(verbosity, 'Updated ResourceAttribute '
                '{}'.format(obj), 2, indent=4)
            for change in changes:
                for fld, rec in changes.items():
                    verbose_msg(verbosity, 'Field {}: {} => {}'.format(
                        fld, rec['old'], rec['new']), 3, indent=8)
        else:
            verbose_msg(verbosity, 'ResourceAttribute {} exists, no '
                    'changes needed.'.format(obj), 3, indent=4)
    return

def create_or_update_project_by_title(fields):
    """Create or update Project with given title.

    Allowed fields are:
        title:
        pi: username of PI
        description:
        field_of_science:
        status: Defaults to 'Active'
        force_review: (construcvtor defaults)
        requires_review: (constructor defaults)
        primary_organization:
        organizations: This should be a list of dicts with keys
            "organization" and "is_primary", or an instance of Organization
            or a fullcode for an Organization.  The value of the "organization"
            key should be an Organization instance or fullcode.  These 
            organizations will become the organizations associated with
            the Project; any previously defined Organizations not found in
            this list will be deleted.
            If the first entry in the list is not a dict or is missing the
            is_primary key, we will default is_primary to true for that
            entry.  For all other entries, is_primary defaults to false.
        add_organizations: Same format as organizations, but previously
            defined Organizations for the Project not in this list will not
            be deleted (although may get demoted to "secondary" orgs if
            an element in this list is flagged as is_primary).
        del_organizations: Same format as organizations, except the
            is_primary key, if present, is completely ignored.  These
            organizations will be removed from the Project
        users, add_users, del_users:
        managers, add_managers, del_managers:
    """
    created = False
    changes = {}
    title = fields['title']

    qset = Project.objects.filter(title=title)
    if qset:
        # Found a project
        proj = qset[0]
        if 'pi' in fields:
            pname = fields['pi']
            if pname is None:
                pi = None
            else:
                pi = User.objects.get(username=pname)
            old = proj.pi
            if old is None:
                if pi is not None:
                    proj.pi = pi
                    proj.save()
                    changes['pi'] = { 'old':old.username, 'new':pname }
            else: 
                if pi is None or old != pi:
                    proj.pi = pi
                    proj.save()
                    changes['pi'] = { 'old':old.username, 'new':pname }
        if 'field_of_science' in fields:
            fosname = fields['field_of_science']
            if fosname is None:
                fos = None
            else:
                fos = FieldOfScience.objects.get(description=fosname)
            old = proj.field_of_science
            if old is None:
                if fos is not None:
                    proj.field_of_science = fos
                    proj.save()
                    changes['field_of_science'] = { 'old':None, 'new':fosname }
            else:
                if fos is None or fos != old:
                    proj.field_of_science = fos
                    proj.save()
                    changes['field_of_science'] = { 
                            'old':old.description, 'new':fosname }

        if 'status' in fields:
            sname = fields['status']
            if sname is None:
                status = None
            else:
                status = ProjectStatusChoice.objects.get(name=sname)
            old = proj.status
            if old is None:
                if status is not None:
                    proj.status = status
                    proj.save()
                    changes['status'] = { 'old':None, 'new':sname }
            else:
                if status is None or sname != old.name:
                    proj.status = status
                    proj.save()
                    changes['status'] = { 'old':old.name, 'new':sname }

        fnames = [ 'force_review', 'requires_review' ]
        for fld in fnames:
            if fld in fields:
                new = fields[fld]
                old = getattr(proj, fld)
                if old != new:
                    setattr(proj, fld, new)
                    proj.save()
                    changes[fld] = { 'old':old, 'new':new }
    else: #if qset:
        created = True
        args = {}
        args['title'] = title
        if 'pi' in fields:
            piname = fields['pi']
            if piname is None:
                raise IntegrityError('Cannot create Project "{}" w/out PI'.format(
                    title))
            else:
                pi = User.objects.get(username=piname)
            args['pi'] = pi
        else:
            raise IntegrityError('Cannot create Project "{}" w/out PI'.format(
                title))
        if 'field_of_science' in fields:
            fosname = fields['field_of_science']
            if fosname is None:
                fos = None
            else:
                fos = FieldOfScience.objects.get(description=fosname)
            args['field_of_science'] = fos
        if 'status' in fields:
            sname = fields['status']
        else:
            # Default status to Active
            sname = 'Active'
        if sname is None:
            sname = 'Active'
        status = ProjectStatusChoice.objects.get(name=sname)
        args['status'] = status

        fnames = [ 'description', 'force_review', 'requires_review' ]
        for fld in fnames:
            if fld in fields:
                args[fld] = fields[fld]

        proj = Project.objects.create(**args)

    #end: if qset:
        
    # Add project managers
    # For now, we only handle 'managers' field
    piname = fields['pi']
    role = ProjectUserRoleChoice.objects.get(name='Manager')
    status = ProjectUserStatusChoice.objects.get(name='Active')
    if 'managers' in fields:
        unames = fields['managers']
    else:
        unames = [ piname ]
    for uname in unames:
        user = User.objects.get(username=uname)
        qset = ProjectUser.objects.filter(user=user, project=proj)
        if qset:
            puser = qset[0]
            if puser.role != role:
                puser.role = role
                puser.save()
                changes['ProjectUser={}-role'.format(uname)] = {
                        'old':puser.role.name, 'new':role.name }
            if puser.status != status:
                puser.status = status
                puser.save()
                changes['ProjectUser={}-status'.format(uname)] = {
                        'old':puser.status.name, 'new':status.name }
        else:
            puser = ProjectUser.objects.create(
                    user=user, project=proj, role=role, status=status)
            changes['ProjectUser={}-role'.format(uname)] = {
                    'old':None, 'new':role.name }
    #end: for uname in unames:

    # Add project users
    # For now, we only handle 'users' field
    role = ProjectUserRoleChoice.objects.get(name='User')
    if 'users' in fields:
        unames = fields['users']
    else:
        unames = []
    for uname in unames:
        user = User.objects.get(username=uname)
        qset = ProjectUser.objects.filter(user=user, project=proj)
        if qset:
            puser = qset[0]
            if puser.role != role:
                puser.role = role
                puser.save()
                changes['ProjectUser={}-role'.format(uname)] = {
                        'old':puser.role.name, 'new':role.name }
        else:
            puser = ProjectUser.objects.create(
                    user=user, project=proj, role=role, status=status)
            changes['ProjectUser={}-role'.format(uname)] = {
                    'old':None, 'new':role.name }
    #end: for uname in unames:

    # Process organizations
    if 'organizations' in fields:
        orgs = fields['organizations']
        tmpchanges = OrganizationProject.set_organizations_for_project(
                project=proj,
                organization_list=orgs,
                delete=True,
                default_first_primary=True,
            )
        changes.update(tmpchanges)
    if 'add_organizations' in fields:
        orgs = fields['add_organizations']
        tmpchanges = OrganizationProject.set_organizations_for_project(
                project=proj,
                organization_list=orgs,
                delete=False,
                default_first_primary=False,
            )
        changes.update(tmpchanges)
    if 'del_organizations' in fields:
        orgs = fields['del_organizations']
        tmpchanges = OrganizationProject.delete_organizations_for_project(
                project=proj,
                organization_list=orgs,
            )
        changes.update(tmpchanges)

    return proj, created, changes

def create_projects_from_dictlist(dlist, verbosity=None):
    """Calls create_or_update_project_by_title for each record in dlist.
    """
    verbose_msg(verbosity, 'Creating Projects...')
    for rec in dlist:
        obj, created, changes = create_or_update_project_by_title(rec)
        if created:
            verbose_msg(verbosity, 'Created Project "{}"'.format(
                obj.title), 2, indent=4)
        elif changes:
            verbose_msg(verbosity, 'Updated Project "{}"'.format(
                obj.title), 2, indent=4)
            for change in changes:
                for fld, rec in changes.items():
                    verbose_msg(verbosity, 'Field {}: {} => {}'.format(
                        fld, rec['old'], rec['new']), 3, indent=8)
        else:
            verbose_msg(verbosity, 'Project "{}" exists, no '
                    'changes needed'.format(
                        obj.title), 3, indent=4)
    return

def create_aattribute_type_by_name(fields):
    """Create an AttributeType for Allocation by name, if needed.

    Returns a doublet (obj, created)
    where
        obj is the new or previously-existing AttributeType
        created is a boolean which is true if a new AttributeType was created
    """
    name = fields['name']
    obj, created = AAttributeType.objects.get_or_create(name=name)
    return obj, created

def create_aattributes_from_dictlist(dlist, verbosity=None):
    """Calls create_aattribute_type_by_name for each dict in dlist
    """
    verbose_msg(verbosity, 'Creating AttributeTypes (for Allocations)...')
    for rec in dlist:
        obj, created = create_aattribute_type_by_name(rec)
        if created:
            verbose_msg(verbosity, 'Created (Allocation) AttributeType {}'.format(
                obj), 2, indent=4)
        else:
            verbose_msg(verbosity, '(Allocation) AttributeType {} exists, no '
                    'changes needed'.format(obj), 3, indent=4)
    return

def create_or_update_allocationattributetype_by_name(fields):
    """Create or update a AllocationAttributeType by name, as needed.

    Checks for existance of AllocationAttributeType with specified name.
    If it exists, update description if needed.  If not, create AllocationAttributeType.

    Fields can have fields:
        name: Name of AllocationAttributeType, required
        attribute_type: Name of (Allocation) AttributeType
        has_usage:
        is_required:
        is_unique:
        is_private:
        is_changeable:
        is_value_unique:

    Returns a triplet (obj, created, changes)
    where
        obj is the new or previously-existing AttributeType
        created is a boolean which is true if a new AttributeType was created
        changes: For updated objects, this is dict keys on fields changed, which
            is dict with keys old and new for old nad new values
    """
    created = False
    changes = {}
    name = fields['name']

    qset = AllocationAttributeType.objects.filter(name=name)
    if qset:
        # We have a AllocationAttributeType with specified name
        obj = qset[0]
        if 'attribute_type' in fields:
            old = obj.attribute_type
            newname = fields['attribute_type']
            if newname is not None:
                new = AAttributeType.objects.get(name=newname)
            else:
                new = None
            if old != new:
                obj.attribute_type = new
                obj.save()
                changes['attribute_type'] = { 'old':old, 'new':new }

        fnames = [ 'has_usage', 'is_required', 'is_unique', 'is_private', 'is_changeable' ]
        for fld in fnames:
            if fld in fields:
                new = fields[fld]
                old = getattr(obj, fld)
                if old is None:
                    if new is not None:
                        setattr(obj, fld, new)
                        obj.save()
                        changes[fld] = { 'old':old, 'new':new }
                else:
                    if new is None or old != new:
                        setattr(obj, fld, new)
                        obj.save()
                        changes[fld] = { 'old':old, 'new':new }
            #end if fld in fields
        #end for fld in fnames
    else: #if qset
        created = True
        args = {}
        args['name'] = name
        if 'attribute_type' in fields:
            newname = fields['attribute_type']
            if newname is None:
                newname = 'Text'
        else:
            newname = 'Text'
        new = AAttributeType.objects.get(name=newname)
        args['attribute_type'] = new

        # These default in constructor
        fnames = [ 'has_usage', 'is_required', 'is_unique', 'is_private', 'is_changeable' ]
        for fname in fnames:
            if fname in fields:
                args[fname] = fields[fname]

        obj = AllocationAttributeType.objects.create(**args)

    return obj, created, changes

def create_allocationattributetypes_from_dictlist(dlist, verbosity=None):
    """Calls create_or_update_allocationattributetype_by_name for each record in dlist.
    """
    verbose_msg(verbosity, 'Creating AllocationAttributeTypes...')
    for rec in dlist:
        obj, created, changes = create_or_update_allocationattributetype_by_name(rec)
        if created:
            verbose_msg(verbosity, 'Created AllocationAttributeType {}'.format(
                obj.name), 2, indent=4)
        elif changes:
            verbose_msg(verbosity, 'Updated Resource '
                '{}'.format(obj), 2, indent=4)
            for change in changes:
                for fld, rec in changes.items():
                    verbose_msg(verbosity, 'Field {}: {} => {}'.format(
                        fld, rec['old'], rec['new']), 3, indent=8)
        else:
            verbose_msg(verbosity, 'AllocationAttributeType {} exists, no '
                    'changes needed'.format(
                        obj.name), 3, indent=4)
    return

def create_or_update_allocation_by_project_resource(fields):
    # This is flawed --- we can have multiple allocs for same PI for same resource
    """Create or update a Allocation by Resource and Project, as needed.

    Checks for existance of Allocation with specified Project and Resource
    If it exists, update other fields as needed.  If not, create Allocation

    Fields can have fields:
        project: Name of Project, required
        resources: List ref of Resource names, required
        status: AllocationStatusChoice name
        quantity: defaulted in constructor
        start_date: defaults to today's date if constructing
        end_date: defaults to today's date if constructing
        justification:
        description:
        is_locked
        is_changeable
        users, add_users, del_users: These need to be updated
            to handle different statuses.  Currently just lists
            of usernames and status will be Active
        allocation_attributes: list of dicts with keys
            'allocation_attribute_type' and 'value'

    Returns a triplet (obj, created, changes)
    where
        obj is the new or previously-existing AttributeType
        created is a boolean which is true if a new AttributeType was created
        changes: For updated objects, this is dict keys on fields changed, which
            is dict with keys old and new for old nad new values
    """
    created = False
    changes = {}
    pname = fields['project']
    if pname is None:
        project = None
    else:
        project = Project.objects.get(title=pname)

    rsrcs = fields['resources']
    resources = []
    rnames = []
    for rname in rsrcs:
        if rname is not None:
            rsrc = Resource.objects.get(name=rname)
            resources.append(rsrc)
            rnames.append(rname)
    rnames.sort()

    qset = Allocation.objects.filter(project=project, resources__in=resources)
    if qset:
        # Allocation already exists
        alloc = qset[0]

        if 'status' in fields:
            sname = fields['status']
            if sname is not None:
                status = AllocationStatusChoice.objects.get(name=sname)
            old = alloc.status
            if old is None:
                if status is not None:
                    alloc.status = status
                    alloc.save()
                    changes['status'] = { 'old':None, 'new':sname }
            else:
                if status is None or old != status:
                    alloc.status = status
                    alloc.save()
                    changes['status'] = { 'old':old.name, 'new':sname }

        fnames = [ 'start_date', 'end_date', 'quantity', 'justification', 
                'description', 'is_locked', 'is_changeable' ]
        for fld in fnames:
            if fld in fields:
                new = fields[fld]
                old = getattr(alloc, fld)
                if old is None:
                    if new is not None:
                        setattr(alloc, fld, new)
                        alloc.save()
                        changes[fld] = { 'old':old, 'new':new }
                else:
                    if new is None or new != old:
                        setattr(alloc, fld, new)
                        alloc.save()
                        changes[fld] = { 'old':old, 'new':new }
                #end: if old is None:
            #end: if fld in fields:
        #end: for fld in fnames:
    else: #if qset:
        # Allocation needs to be created
        args = {}
        args['project'] = project

        if 'status' in fields:
            sname = fields['status']
        else:
            sname = 'Active'
        if sname is None:
            sname = 'Active'
        status = AllocationStatusChoice.objects.get(name=sname)
        args['status'] = status

        fnames = [ 'start_date', 'end_date', 'quantity', 'justification', 
                'description', 'is_locked', 'is_changeable' ]
        for fld in fnames:
            if fld in fields:
                args[fld] = fields[fld]

        alloc = Allocation.objects.create(**args)
        # And set resources
        alloc.resources.set(resources)

    # Update Allocation Users as needed
    users2add = set()
    users2del = []
    added_users = []
    deled_users = []
    old_users = []
    if 'users' in fields:
        usernames = fields['users']
        users2add = users2add.union( set(usernames) )
    if 'add_users' in fields:
        users2add = users2add.union( fields['add_users'])
    if 'rem_users' in fields:
        users2del = fields['del_users']
    auser_status_list = AllocationUserStatusChoice.objects.all()
    auser_status_by_name = {}
    for auser_status in auser_status_list:
        auser_status_by_name[auser_status.name] = auser_status
    austatus_removed = auser_status_by_name['Removed']
    austatus_active = auser_status_by_name['Active']
    for auser_obj in auser_status_list:
        key = auser_obj.name
        auser_status_by_name[key] = auser_obj
    for auser in AllocationUser.objects.filter(allocation=alloc):
        auname = auser.user.username
        old_users.append(auname)
        if auname in users2del:
            deled_users.append(auname)
            if auser.status != austatus_removed:
                auser.status = austatus_removed
                auser.save()
                changes['AllocationUser:{}'.format(auname)] = {
                        'old':auser.status, 'new':'Removed' }
                users2add.remove(auname)
        elif auname in users2add:
            deled_users.append(auname)
            if auser.status != austatus_active:
                auser.status = austatus_active
                auser.save()
                changes['AllocationUser:{}'.format(auname)] = {
                        'old':auser.status, 'new':'Active' }
        else:
            deled_users.append(auname)
            if auser.status != austatus_removed:
                auser.status = austatus_removed
                auser.save()
                changes['AllocationUser:{}'.format(auname)] = {
                        'old':auser.status, 'new':'Removed' }
                deled_users.append(auname)
    for auname in users2add:
        user = User.objects.get(username=auname)
        auser = AllocationUser.objects.create(
                allocation=alloc, user=user, status=austatus_active)
        changes['AllocationUser:{}'.format(auname)] = {
                'old':'NOT PRESENT', 'new':'Active' }

    # Add AllocationAttributes as needed
    if 'allocation_attributes' in fields:
        attrib_list = fields['allocation_attributes']
        for aarec in attrib_list:
            aatname = aarec['allocation_attribute_type']
            aatype = AllocationAttributeType.objects.get(name=aatname)
            if 'value' in aarec:
                value = aarec['value']
            else:
                value = None

            qset = AllocationAttribute.objects.filter(
                    allocation=alloc, allocation_attribute_type=aatype)
            if qset:
                # Allocation Attribute exists
                aattrib = qset[0]
                old = aattrib.value
                if old != value:
                    aattrib.value = value
                    aattrib.save()
                    changes['AllocationAttribute-{}'.format(aatname)]= {
                            'old':old, 'new':value }
            else: #if qset
                # No AllocationAttribute previously existing, create
                aattrib = AllocationAttribute.objects.create(
                        allocation=alloc,
                        allocation_attribute_type=aatype,
                        value = value,
                        )
                changes['AllocationAttribute-{}'.format(aatname)]= {
                        'old':None, 'new':value }
            #end: if qset
        #end: for aarec in attrib_list
    #end: if 'allocation_attributes' in fields:

    return alloc, created, changes

def create_allocation_from_dict(fields):
    """Create or update an Allocation, as needed.

    Creates an Allocation with specified Project and Resource
    Will also add users and AllocationAttributes

    Fields can have fields:
        project: Name of Project, required
        resources: List ref of Resource names, required
        status: AllocationStatusChoice name
        quantity: defaulted in constructor
        start_date: defaults to today's date if constructing
        end_date: defaults to today's date if constructing
        justification:
        description:
        is_locked
        is_changeable
        #Since new alloc, only need a single users field
        users: list of usernames of users to add to alloc (as active)
            Defaults to all active project users
        removed_users: list of usernames of users to add to alloc (as Removed)
            Defaults to empty list
        error_users: list of usernames of users to add to alloc (as Error)
            Defaults to empty list
        allocation_attributes: list of dicts with keys
            'allocation_attribute_type' and 'value'

    Returns a triplet (obj, created, changes)
    where
        obj is the new Allocation
        created is a boolean which is true if a new AttributeType was created
        changes: For updated objects, this is dict keys on fields changed, which
            is dict with keys old and new for old nad new values
        created will always be True, changes will always be empty
    """
    created = False
    changes = {}
    args = {}

    pname = fields['project']
    if pname is None:
        project = None
    else:
        project = Project.objects.get(title=pname)
    args['project'] = project

    rsrcs = fields['resources']
    resources = []
    rnames = []
    for rname in rsrcs:
        if rname is not None:
            rsrc = Resource.objects.get(name=rname)
            resources.append(rsrc)
            rnames.append(rname)
    rnames.sort()

    if 'status' in fields:
        sname = fields['status']
    else:
        sname = 'Active'
    if sname is None:
        sname = 'Active'
    status = AllocationStatusChoice.objects.get(name=sname)
    args['status'] = status

    fnames = [ 'start_date', 'end_date', 'quantity', 'justification', 
            'description', 'is_locked', 'is_changeable' ]
    for fld in fnames:
        if fld in fields:
            args[fld] = fields[fld]

    alloc = Allocation.objects.create(**args)
    # And set resources
    alloc.resources.set(resources)

    # Add Allocation Users as needed
    #   Active users
    status = AllocationUserStatusChoice.objects.get(name='Active')
    unames = []
    if 'users' in fields:
        unames = fields['users']
    else:
        qset = ProjectUser.objects.filter(project=project, status__name='Active')
        unames = [x.user.username for x in qset]
    for uname in unames:
        user = User.objects.get(username=uname)
        auser = AllocationUser.objects.create(
                allocation=alloc, user=user, status=status)
        changes['AllocationUser-{}-status'.format(uname)] = {
                'old':None, 'new':status.name }

    #    Removed users
    status = AllocationUserStatusChoice.objects.get(name='Removed')
    unames = []
    if 'removed users' in fields:
        unames = fields['removed_users']
    else:
        unames = []
    for uname in unames:
        user = User.objects.get(username=uname)
        auser = AllocationUser.objects.create(
                allocation=alloc, user=user, status=status)
        changes['AllocationUser-{}-status'.format(uname)] = {
                'old':None, 'new':status.name }

    #    Errored users
    status = AllocationUserStatusChoice.objects.get(name='Error')
    unames = []
    if 'error users' in fields:
        unames = fields['error_users']
    else:
        unames = []
    for uname in unames:
        user = User.objects.get(username=uname)
        auser = AllocationUser.objects.create(
                allocation=alloc, user=user, status=status)
        changes['AllocationUser-{}-status'.format(uname)] = {
                'old':None, 'new':status.name }

    # Add AllocationAttributes as needed
    if 'allocation_attributes' in fields:
        attrib_list = fields['allocation_attributes']
        for aarec in attrib_list:
            aatname = aarec['allocation_attribute_type']
            aatype = AllocationAttributeType.objects.get(name=aatname)
            if 'value' in aarec:
                value = aarec['value']
            else:
                value = None

            qset = AllocationAttribute.objects.filter(
                    allocation=alloc, allocation_attribute_type=aatype)
            if qset:
                # Allocation Attribute exists
                aattrib = qset[0]
                old = aattrib.value
                if old != value:
                    aattrib.value = value
                    aattrib.save()
                    changes['AllocationAttribute-{}'.format(aatname)]= {
                            'old':old, 'new':value }
            else: #if qset
                # No AllocationAttribute previously existing, create
                aattrib = AllocationAttribute.objects.create(
                        allocation=alloc,
                        allocation_attribute_type=aatype,
                        value = value,
                        )
                changes['AllocationAttribute-{}'.format(aatname)]= {
                        'old':None, 'new':value }
            #end: if qset
        #end: for aarec in attrib_list
    #end: if 'allocation_attributes' in fields:

    return alloc, created, changes

def create_allocations_from_dictlist(dlist, verbosity=None):
    """Calls create_allocation_from_dict for each dict in dlist
    """
    verbose_msg(verbosity, 'Creating Allocations...')
    for rec in dlist:
        obj, created, changes = create_allocation_from_dict(rec)
        if created:
            verbose_msg(verbosity, 'Created Allocation {}'.format(
                obj), 2, indent=4)
        elif changes:
            verbose_msg(verbosity, 'Updated Allocation '
                '{}'.format(obj), 2, indent=4)
            for change in changes:
                for fld, rec in changes.items():
                    verbose_msg(verbosity, 'Field {}: {} => {}'.format(
                        fld, rec['old'], rec['new']), 3, indent=8)
        else:
            verbose_msg(verbosity, 'Allocation {} exists, no '
                    'changes needed.'.format(obj), 3, indent=4)
    return
    
