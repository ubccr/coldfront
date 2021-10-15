# Command-line utilities for the Organizational Hierarchy

This page describes the various command line tools for dealing with
the Organizational Hierarchy within ColdFront.

The commands are:
    - [add_organization_defaults](#add_organization_defaults)
    - [import_directory2organizations](#import_directory2organizations)
    - [import_organization_levels](#import_organization_levels)
    - [import_organizations](#import_organizations)
    - [list_projects_by_organization](#list_projects_by_organization)
    - [list_users_by_organization](#list_users_by_organization)
    - [update_user_organizations_from_ldap](#update_user_organizations_from_ldap)

## add_organization_defaults {#add_organization_defaults}

This command is generally not invoked directly but gets invoked as 
part of the standard ColdFront `initial_setup` command.

It basically sets up the default
```
_University_ > _College_ > _Department_ 
```
OrganizationLevels.


## import_directory2organizations {#import_directory2organizations}

This command allows for importing entries into the
Directory2Organization model, as described in the [ldap integrations](ldap.md#dir2org) 
page.

In addition to the standard ColdFront command line arguments, this command 
takes the arguments:
    * `--input INPUTFILE`: the name of input file to read.
    * `--delimiter DELIM`: the field delimiter to use
    * `--delete`: If this flag is given, delete existing data in table before importing

The delimiter defaults to the pipe ('|') character.

The name of the input file defaults to `directory2organization.csv` in the `local_data`
subdirectory of the `BASE_DIR` directory as set in the configuration files.
The file should have each record on a separate line, with the first field being the
`fullcode` for the Organization, and the second field being the text string for
that Organization as returned by the directory.  So a line like (assuming the default
pipe delimitter):
```
UMD-CMNS-CHEM|CMNS-Chemistry & Biochemistry
```
will cause the string "CMNS-Chemistry & Biochemistry" when returned by the appropriate
LDAP attribute be associated with the Organization with the `fullcode` "UMD-CMNS-CHEM".
Blank lines and lines <em>starting</em> with the octothorpe/pound/number sign ("#") character
are ignored.


## import_organization_levels {#import_organization_levels}

This command allows for importing entries into the
OrganizationLevel model, as described in the [overview](overview.md#orglevels) 
page.

In addition to the standard ColdFront command line arguments, this command 
takes the arguments:
    * `--input INPUTFILE`: the name of input file to read.
    * `--delimiter DELIM`: the field delimiter to use
    * `--delete`: If this flag is given, delete existing data in table before importing

The delimiter defaults to the pipe ('|') character.

The name of the input file defaults to `organization_levels.csv` in the `local_data`
subdirectory of the `BASE_DIR` directory as set in the configuration files.
The file should have each record on a separate line, with fields separated by the
delimiter character.  The fields in order should be: 
1. the name of this OrganizationLevel
1.  the integer level value for this OrganizationLevel 
1. the name of its parent OrganizationLevel (omitted if it has no parent). 
So using the default pipe delimiter,
the default values would be:
```
University|40
College|30|University
Department|20|College
```
Blank lines and lines <em>starting</em> with the octothorpe/pound/number sign ("#") character
are ignored.


## import_organizations {#import_organizations}

This command allows for importing entries into the
Organization model, as described in the [overview](overview.md#orgs) 
page.

In addition to the standard ColdFront command line arguments, this command 
takes the arguments:
    * `--input INPUTFILE`: the name of input file to read.
    * `--delimiter DELIM`: the field delimiter to use
    * `--delete`: If this flag is given, delete existing data in table before importing

The delimiter defaults to the pipe ('|') character.

The name of the input file defaults to `organizations.csv` in the `local_data`
subdirectory of the `BASE_DIR` directory as set in the configuration files.
The file should have each record on a separate line, with fields separated by the
delimiter character.  The fields in order should be: 
1. The code for this Organization
1. The name of the OrganizationLevel associated with this Organization
1. The code of its parent Organization (or blank for no parent)
1. The shortname for this Organization
1. The longname of this Organization
1. The value for the ``is_selectable_for_user`` field, boolean.
1. The value for the ``is_selectable_for_project`` field, boolean.
For the boolean fields, it is recommended that you use 1 for True, and 0 for False.
Blank lines and lines <em>starting</em> with the octothorpe/pound/number sign ("#") character
are ignored.

So using the default pipe delimiter and the default OrganizationLevels, we might
have something like:
```
# Define our universities
UMD|University||UMaryland|University of Maryland|0|0
# ...
# Define our colleges
CMNS|College|UMD|Comp, Math & Natural Scis|College of Computer, Mathematical, and Natural Sciences|0|0
# ...
# Define our departments
CHEM|Department|CMNS|Chemistry|Department of Chemistry & Biochemistry|1|1
# ...
```

This would define an Organization with `fullcode` "UMD-CMNS-CHEM" which is selectable for
User and Projects, and its parents (which are not selectable).

## list_projects_by_organization {#list_projects_by_organization}

This command lists projects based on the [Organizations](overview.md#orgs) to which they belong.

In addition to the standard ColdFront command line arguments, this command 
takes the arguments:
    * `--organization ORG` (or '--org' or '-o' for short): the `fullcode` 
      of the organization we want to match.  May be repeated.
    * `--and`: Match the intersection of multiple organizations given on 
      the command line.
    * `--descendents` (or `--children`): Match projects belong to an 
      Organization that descends from _ORG_
    * `--status STATUS`: Only match projects with status _STATUS_.  
      May be repeated.
    * `--verbosity V`: Controls verbosity of output.

This command will list projects matching the specified status and organization criteria.
If multiple STATUS values are given, a project is considered for display if it belongs
to any of the given statuses.  If the --status flag is omitted, all projects (regardless
of status) are eligible to match.

For each organization ORG given, an eligible project matches if it is directly associated
with ORG, or if the `--descendents`` flag is given and ORG is an ancestor of any of
the Organizations associated with the project.  (By ancestor, we mean the parent of an
Organization, or the parent of the parent, etc. until we arrive at an ancestor without a
parent.)  

If multiple ORG values are given on the command line, by default we consider a project
to match if it matches _any_ of the given ORG values (i.e. the union of the matches of
the individual ORG values).  But if the `--and` flag is given, a project is considered 
to match only if it matches _all_ ORG values (i.e. the intersection of the matches of
the individual ORG values).

The terse output (for verbosity 0) is to just list the names of the matching projects.
The normal output (verbosity 1 or greater) lists the name of matching projects, followed
by the username of the PI in parentheses, and the status in brackets ([]).

## list_users_by_organization {#list_users_by_organization}

This command lists users based on the [Organizations](overview.md#orgs) to which they belong.

In addition to the standard ColdFront command line arguments, this command 
takes the arguments:
    * `--organization ORG` (or '--org' or '-o' for short): the `fullcode` 
      of the organization we want to match.  May be repeated.
    * `--and`: Match the intersection of multiple organizations given 
      on the command line.
    * `--descendents` (or `--children`): Match projects belong to an 
      Organization that descends from _ORG_
    * `--inactive`: This allows matching inactive as well as active users.
    * `--verbosity V`: Controls verbosity of output.

This command will list users matching the specified status and organization criteria.
Normally only active users are considered for matching; if the `--inactive`` flag
is given both active and inactive users are eligible for matching.

For each organization ORG given, an eligible user matches if it is directly associated
with ORG, or if the `--descendents`` flag is given and ORG is an ancestor of any of
the Organizations associated with the user.  (By ancestor, we mean the parent of an
Organization, or the parent of the parent, etc. until we arrive at an ancestor without a
parent.)  

If multiple ORG values are given on the command line, by default we consider a user
to match if it matches _any_ of the given ORG values (i.e. the union of the matches of
the individual ORG values).  But if the `--and` flag is given, an user is considered 
to match only if it matches _all_ ORG values (i.e. the intersection of the matches of
the individual ORG values).

The terse output (for verbosity 0) is to just list the usernames of the matching users.
The normal output (verbosity 1 or greater) lists the username of matching users, followed
by a colon (':'), their last, first names, and their status in brackets([]).

## update_user_organizations_from_ldap {#update_user_organizations_from_ldap}

This command will update the [Organizations](overview.md#orgs) associated with
an user based on an LDAP lookup.  It requires the 
[LDAP User Search](https://github.com/ubccr/coldfront/tree/master/coldfront/plugins/ldap_user_search)
plugin for ColdFront to be enabled, and the 
[ORGANIZATION_LDAP_USER_ATTRIBUTE](configuration.md#ORGANIZATION_LDAP_USER_ATTRIBUTE) variable
to be appropriately set.  The command will be most useful if
the [Directory2Organization model](ldap.md#dir2org) is populated.

In addition to the standard ColdFront command line arguments, this command 
takes the arguments:
    * `--user USER` (or '-u' for short): the username of the user to update. May be repeated.
    * `--all`: Update all (active) users
    * `--parents`: Associate any ancestors of Organizations from LDAP for the user.
    * `--delete`: Disassociates any Organizations of user not found in LDAP
    * `--create-placeholder` (or `--placeholder` for short): Create placeholder 
      orgs for values not found in Directory2Organization
    * `--dryrun`: Do not actually do anything, just state what would have done.
    * `--verbosity V`: Controls verbosity of output.

The `--dryrun` option keeps the command from making any changes, but just has it
go through the motions and print what it would have done.  If forces a verbosity of
at least 1.  

If `--all` is given, the command acts on all (active) users found in ColdFront.
If `--user` is given, it only acts on the specified users --- if provided more than
once, it acts on all users provides.  Users should be specified by username.
The `--all` and `--user` options are mutually exclusive, but at least one of them
must be provided.

For each user being processed, the command will look the user up in LDAP, using the
configuration/codes from the LDAP user search plugin.  If the user
is not found in LDAP, the user is skipped.  If the user is found, we look at the values
of the attribute specified by ORGANIZATION_LDAP_USER_ATTRIBUTE.  These values
are compared to the `directory_string` field of the [Directory2Organization](ldap.md#dir2org)
model, and if a match is found, that Organization is placed in a list of Organizations
for that UserProfile. 

If a match for the attribute value is not found in the Directory2Organization table, 
the default behavior is simply to ignore that string and move on to the next attribute 
value if any.  If the ``create-placeholder` flag was set and the attribute value
was not found in the Directory2Organzation table, then we:
1. Create an "Unknown" Organization at the "University" OrganizationLevel (or 
   whatever top-level OrganizationLevel you have defined) if one does not 
   already exist.
1. Create a "placeholder" Organization with code "Unknown_xxxxx" (replacing 
   the x-es with some random string), with the "Unknown" University 
   Organization as its parent.  The longname will include the string which
   could not be matched.
1. Add this "placeholder" Organization to the list of Organizations for 
   that UserProfile.
This process facilitates an administrator later viewing the various placeholder
organizations (which should be the only children of `Unknown`).  The admin
can then see if that LDAP string corresponds to an already existing Organization
or represents a new Organization.

In the existing Organization case he/she can edit the corresponding entry 
for the LDAP string in the Directory2Organization model to point to the
correct Organization, and either find all the UserProfiles associated with the 
placeholder and manually change them to be associated with the existing 
organization (and if desired its ancestors) or re-run this command for the 
affected users and then delete the placeholder.

In the new Organization case, the admin can just edit the placeholder object to 
represent the new Organization (e.g. set the code, organization level, parent, 
and names).  The Directory2Organization string will be fine, and the UserProfiles
will point to the correct Organization --- the only possibly modifications needed
are to add the ancestors if needed and desired.

Once all of the values for the attribute have been processed, the
command will add any Organizations from the list of Organizations for
that UserProfile to the UserProfile.  If the `--delete` flag is given, 
any Organizations to which the UserProfile is associated that were not in
the list of Organizations for the UserProfile will then be disassociated
with the profile.

