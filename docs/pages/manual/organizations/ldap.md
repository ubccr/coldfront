# Integrating the Organizations with LDAP

This page discusses some topics related to integrating the
[Organization](overview.md#orgs) hierarchy for UserProfiles 
with LDAP.  At this time,
there is no integration between Project Organizations and LDAP.

The integration requires that either (or both of) the
    - [LDAP User Search](https://github.com/ubccr/coldfront/tree/master/coldfront/plugins/ldap_user_search)
    - `LDAP Auth`
ColdFront plugins be enabled and configured.

It also requires that the 
[ORGANIZATION_LDAP_USER_ATTRIBUTE](configuration.md#ORGANIZATION_LDAP_USER_ATTRIBUTE)
be set to give the name of an LDAP attribute on users that returns a list 
of string values which correlate to organizations within your hierarchy.

If you are using the `LDAP Auth` plugin for ColdFront, you can configure it to
collect that attribute whenever the user logs in, and update the list of 
organizations for the user.  

If you are using the `LDAP User Search` plugin for ColdFront, you can run
the command [update_user_organizations_from_ldap](cmdline.md#update_user_organizations_from_ldap)
to lookup the attribute for specified or all users and update the list of
Organizations for them accordingly.

1. The [Directory2Organization model](#dir2orgs)
1. [Integrating with the LDAP Auth plugin](#ldapauth)
1. [Integrating with the LDAP User Search plugin](#ldapsearch)

## Directory2Organization {#dir2orgs}

Because we do not assume that the strings returned by the
[ORGANIZATION_LDAP_USER_ATTRIBUTE](configuration.md#ORGANIZATION_LDAP_USER_ATTRIBUTE)
attribute will exactly match the Organizations as implemented in
the [Organization model](overview.md#orgs), we need a mechanism for
translating.  This is the Directory2Organization model.

Directory2Organization is a simple model that just relates a text 
string to an Organization.  Each text string is assumed to relate
to a single entry in the Organization table.  However, we allow for
multiple strings to relate to the same Organization; this can be
useful if the institutional organizational model is more finely
grained than you want to use for ColdFront, at least in certain
areas (e.g. if there are several groups within the IT unit which
access the cluster for administrative purposes but you do not
wish to distinguish between them for reporting, etc. purposes,
you can have them all just map to a common parent).  It also
allows for you to "lie" to ColdFront if desired (e.g. if the
HPC is run out of the Research Division, but some administrators
are institutionally in a subbranch of the IT Division, you can 
tell ColdFront to consider that subbranch as part of the Research
Division.  This of course should be used sparingly, as it 
affects all members of the subbranch who appear in ColdFront).

The command [import_directory2organizations_from_ldap](cmdline.md#import_directory2organizations_from_ldap)
can be used to import a list of such associations from a file.

### Placeholder Organizations {#placeholder}

To assist with populating the [Directory2Organization](#dir2orgs) table, 
it is possible to allow for the codes which update the 
[Organization](overview.md#orgs) list for an UserProfile to operate in
"create-placeholder" mode.  This can be set via a flag on the 
[update_user_organizations_from_ldap](cmdline.md#update_user_organizations_from_ldap)
command, or via the configuration variable
[ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS](configuration.md#ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS)
when integrating with the LDAP Auth plugin.

In either case, ColdFront retrieves a list of strings from the LDAP attribute
specified by 
[ORGANIZATION_LDAP_USER_ATTRIBUTE](configuration.md#ORGANIZATION_LDAP_USER_ATTRIBUTE)
for the user in question, and then uses the Directory2Organization table
to map these strings onto organizations in the Organization table.

When not running in "create-placeholder" mode, if a string from the attribute
does not match an entry in the Directory2Organization table, it is simply
ignored.  While this is reasonable behavior, it means that this information
will be lost to ColdFront (at least until the string is entered into the
Directory2Organization table).

When running in "create-placeholder" mode, if a string does not match an
entry in the Directory2Organization table, the code will:
1. Create an Organization with code "Unknown" at the top OrganizationLevel 
   (e.g. at "University" level in the default case), if such an Organization
   does not already exist.
1. Create a "placeholder"  Organization at the OrganizationLevel just below 
   the top level (e.g. "College" level in the default case), with parent 
   "Unknown" for the unrecognized LDAP attribute string.  The `code` for this
   Organization will begin "Unknown_" followed by a long, unique string of
   characters.  The `longname` will include the unrecognized string in it.
1. Create a Directory2Organization entry linking the unrecognized string to
   this "placeholder" Organization (so in the future, that string will no 
   longer be unrecognized).  
1. Associate this "placeholder" Organization to the UserProfile in question.
1. Any other users processed in the future that also have this LDAP attribute
   string returned will find the string in Directory2Organizations, and so
   the "placeholder" Organization will be associated with them.

The advantage of this approach is that at a later date an adminsitrator can
look at children of the "Unknown" Organization and see all of the placeholder
Organizations, and can process each of them.  

If the placeholder represents a new Organization that was missing, the
admin can simply manually rename the placeholder Organization and move it 
to the appropriate place in the organizational hierarchy (creating parent 
Organizations as needed).  The Directory2Organization will still cause the
original directory LDAP attribute string to map to the (no longer a placeholder)
Organization, and the users found with that attribute string will
already be in the group, so that is all which should need to be done for
that case.

If the attribute string from LDAP that caused the creation of the placeholder
should have mapped onto an existing Organization, then the process is a bit
more complicated.  The admin will need to edit the Directory2Organization entry
to point the attribute string to the correct Organization.  The admin will then
need to check all of the members of the placeholder Organization and add the
Organization the string was supposed to map to the UserProfile for the member
(assuming they were not already in the Organization).  After that is done
for all members of the placeholder Organization, the placeholder can be
deleted.  While not as simple as the new Organization case, it is still not
very onerous.

## Integrating with the LDAP Auth plugin {#ldapauth}

If the configuration variable
[ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS](configuration.md#ORGANIZATION_LDAP_AUTH_POPULATE_USER_ORGANIZATIONS)
is set to True (or 1 if using environmental variables), then ColdFront
will have a function `populate_user_organizations` handle the 
`populate_user` signal, which is generated whenever someone authenticates
using the LDAP Auth plugin.  That function in turn calls the 
Organization.update_user_organizations_from_dirstrings class method, 
which will update the Organizations associated with that UserProfile
according to the values received in the 
[ORGANIZATION_LDAP_USER_ATTRIBUTE](configuration.md#ORGANIZATION_LDAP_USER_ATTRIBUTE),
after translating them via the [Directory2Organization](#dir2orgs) table.

Other configuration variables of note:
   - [ORGANIZATION_LDAP_USER_ADD_PARENTS](configuration.md#ORGANIZATION_LDAP_USER_ADD_PARENTS):
     if this is set, then for any Organization found for the user, we also 
     add all of the ancestors of the Organization.  If not set, only the
     Organizations explicitly listed for the User will be added.
   - [ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS](configuration.md#ORGANIZATION_LDAP_USER_CREATE_PLACEHOLDERS):
     if this is set, then if a value of the ORGANIZATION_LDAP_USER_ATTRIBUTE does
     not match an entry in the Directory2Organization table, a placeholder
     Organization is created.  This process (and why it might be desirable)
     is described in the documentation for [Directory2Organization](#dir2orgs).
     If not set, entries which do not match are just ignored.
   - [ORGANIZATION_LDAP_USER_DELETE_MISSING](configuration.md#ORGANIZATION_LDAP_USER_DELETE_MISSING):
     If this is set, any Organizations associated with the UserProfile
     that do not match an Organization for a string returned by the
     attribute (or an ancestor of such, if add parents was set) will be
     disassociated with the UserProfile.

## Integrating with the LDAP User Search plugin {#ldapsearch}

The command [update_user_organizations_from_ldap](cmdline.md#update_user_organizations_from_ldap)
can be run manually or as a cron job to periodically update the Organizations
associated with specific users (or all active users).  It is documented in the
[command line documentation](cmdline.md#update_user_organizations_from_ldap).
