# FreeIPA integration for ColdFront

ColdFront django plugin providing FreeIPA integration for ColdFront.
[FreeIPA](https://www.freeipa.org) is an integrated Identity and Authentication
solution for Linux. The idea behind this app is to provide a bridge between
FreeIPA HBAC (host based access control) and ColdFront allocations. With this
app enabled, when a user is added/removed from a allocation, they are also
added/removed from any configured FreeIPA unix groups. If a host has the
appropriate HBAC rule in place to restrict access to only allowed groups then
this can provide a way for PI's in ColdFront to manage access to their
resources. This app also provides searching FreeIPA LDAP when adding users to
projects and allocations.

A command line tool is also provided with this app that allows an administrator
to check the consistency between ColdFront and FreeIPA and optionally sync any
discrepancies. 

## Design

FreeIPA unix groups can be set on a per allocation basis using an
allocation attribute named "freeipa\_group".  The value of this attribute
must be a valid unix group in FreeIPA. Any users added/removed from the
allocation will then automatically be added/removed from the group in
FreeIPA. You can specify more than one group by simply adding multiple
"freeipa\_group" allocation attributes. This app subscribes to specific
ColdFront signals that are sent whenever a user is added or removed from a
allocation and the signals in turn submit jobs to django-q. The tasks run by
django-q are defined in tasks.py and interact with the FreeIPA API using the
ipaclient python library.

## Requirements

### Install required system packages for dbus python

- yum install dbus-devel glib2-devel libsss_simpleifp

### Install required python packages

- uv sync --extra ldap --extra freeipa

### Update sssd.conf to enable infopipe

Edit file /etc/sssd/sssd.conf and add following:

```
[sssd]
services = nss, sudo, pam, ssh, ifp

[ifp]
allowed_uids = root, coldfront-user
user_attributes = +mail, +givenname, +sn, +uid, +nsaccountlock
```

Then restart sssd:

```
$ systemctl restart sssd
$ sss_cache -E
```

## Usage

To enable this plugin set the following environment variables:

```
PLUGIN_FREEIPA=True
FREEIPA_KTNAME='/path/to/user.keytab'
FREEIPA_SERVER='freeipa.localhost.localdomain'
FREEIPA_USER_SEARCH_BASE='cn=users,cn=accounts,dc=example,dc=edu'
```

The "FREEIPA\_KTNAME" should be the path to the keytab file for a user in
FreeIPA with the appropriate permissions for modifying group membership. The
easiest way to do this in FreeIPA is to create a new role for ColdFront with
the "Modify Group membership" privilege. Then create a user account
specifically for use with ColdFront and assign them this role. Then export a
keytab for that user.

## CLI Usage

To check the consistency between ColdFront and FreeIPA run the following command:

```
    $ coldfront freeipa_check -x --verbosity 0
```

This will process all active allocations that have a "freeipa\_group"
attribute and check that active users are members of that group and removed
users are not members of that group in freeipa. You can optionally provide the
'--sync' flag and this tool will modify group membership in FreeIPA. This will
also update user status in ColdFront to match that in freeipa.

```
    $ coldfront freeipa_check --sync
```

To get verbose logging run:

```
    $ coldfront freeipa_check --sync --verbosity 2
```

You can also optionally limit to specific users and groups:

```
    $ coldfront freeipa_check --username jane --group academic --verbosity 2

```
