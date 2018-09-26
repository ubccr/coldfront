# FreeIPA integration for Coldfront

Coldfront django extra app providing FreeIPA integration for Coldfront.
[FreeIPA](https://www.freeipa.org) is an integrated Identity and Authentication
solution for Linux. The idea behind this app is to provide a bridge between
FreeIPA HBAC (host based access control) and Coldfront subscriptions. With this
app enabled, when a user is added/removed from a subscription, they are also
added/removed from any configured FreeIPA unix groups. If a host has the
appropriate HBAC rule in place to restrict access to only allowed groups then
this can provide a way for PI's in Coldfront to manage access to their
resources.

## Design

FreeIPA unix groups can be set on a per subscription basis using using a
subscription attribute named "freeipa\_group".  The value of this attribute
must be a valid unix group in FreeIPA. Any users added/removed from the
subscription will then automatically be added/removed from the group in
FreeIPA. You can specify more than one group by simply adding multiple
"freeipa\_group" subscription attributes. This app subscribes to specific
Coldfront signals that are sent whenever a user is added or removed from a
subscription and submits a job to django-q. The tasks run by django-q are
defined in tasks.py and interact with the FreeIPA API using the ipaclient
python library.

## Requirements

- pip install django-q
- pip install ipaclient

To run django-q:

```
    python manage.py qcluster
```

## Usage

To enable this extra app add or uncomment the following in your
local\_settings.py file:

```
    EXTRA_APPS += [
        'extra.djangoapps.freeipa',
    ]
    FREEIPA_KTNAME = '/path/to/user.keytab'
```

The "FREEIPA\_KTNAME" should be the path to the keytab file for a user in
FreeIPA with the appropriate permissions for modifing group membership. The
easiest way to do this in FreeIPA is to create a new role for Coldfront with
the "Modify Group membership" priviledge. Then create a user account
specifically for use with Coldfront and assign them this role. Then export a
keytab for that user.
