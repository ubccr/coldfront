# Slurm integration for Coldfront

Coldfront django extra app providing Slurm integration for Coldfront.
Subscriptions in Coldfront are marshalled out to Slurm associations in the
Slurm flat file format and can be loaded with sacctmgr. For more information on
the Slurm flat file format see [here](https://slurm.schedmd.com/sacctmgr.html).

## Design

Resources in Coldfront map to Clusters (or partitions within a cluster) in
Slurm. The name of the Slurm cluster is taken from a resource attribute in
Coldfront named "slurm\_cluster".  You can optionally provide Slurm
specifications for a cluster using a resource attribute named "slurm\_specs".
The value of this attribute must conform to the Slurm specification format and
are colon separated.

Subscriptions in Coldfront map to Accounts in Slurm. The name of the Slurm
account is taken from a subscription attribute in Coldfront named
"slurm\_account\_name" . You can optionally provide Slurm specifications for
the account using a subscription attribute named "slurm\_specs". The value of
this attribute must conform to the Slurm specification format and are colon
separated.

Subscription users in Coldfront map to Users in Slurm. You can optionally
provide Slurm specifications for each user in a subscription using a
subscription attribute named "slurm\_user\_specs". The value of this attribute
must conform to the Slurm specification format and are colon separated. Setting
specifications on an individual user basis is not currently supported.

This app also subscribes to specific Coldfront signals that are sent whenever a
user is added or removed from a subscription and submits a job to django-q. The
tasks run by django-q are defined in tasks.py and interact with Slurm using the
sacctmgr command. Anytime a user is removed from a subscription their Slurm
association is removed. You can disable this behavior by setting "SLURM\_NOOP"
to False.

## Requirements

- pip install django-q

To run django-q:

```
    python manage.py qcluster
```

## Usage

To enable this extra app add or uncomment the following in your
local\_settings.py file:

```
    EXTRA_APPS += [
        'extra.djangoapps.slurm',
    ]
    SLURM_NOOP = False
    SLURM_SACCTMGR_PATH = '/usr/bin/sacctmgr' 
```

To generate Slurm association data from Coldfront run the following command:

```
    $ python manage.py sacctmgr_dump -o /output_dir
```

You can then load this file into Slurm with the following command:

```
    $ sacctmgr load file=/output_dir/tux.cfg

```

## Special cases

Resources in Coldfront can optionally be organized into parent/child
relationships. This is useful in the context of Slurm for example if you have a
single Slurm controller with multiple partitions. Each partition represents a
seperate resource in Coldfront that users can subscribe to. In this case you
would create a parent resource that represents your Slurm cluster (or
controller) with a resource type of "Cluster". Each Slurm partition would be a
seperate resource in Coldfront with a resource type of "Partition" and have
their parent resource set to the Slurm cluster. Users wouldn't subscribe to the
parent Slurm cluster resource but only subcribe to the parition resources. Here
you would only set the "slurm\_cluster" resource attribute on the Slurm cluster
resource and not on the partitions. Also, "slurm\_specs" resource attribute on
paritions are merged with the subscription "slurm\_specs" and set on the Slurm
account association instead of the cluster.
