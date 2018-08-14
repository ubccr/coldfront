# Slurm integration for Coldfront

Coldfront django extra app providing Slurm integration for Coldfront.
Subscriptions in Coldfront are marshalled out to Slurm associations in the
Slurm flat file format and can be loaded with sacctmgr. For more information on
the Slurm flat file format see [here](https://slurm.schedmd.com/sacctmgr.html).

## Design

Resources in Coldfront map to Clusters (or partitions within a cluster) in
Slurm. The name of the Slurm cluster is taken from a resource attribute in
Coldfront named "Slurm cluster name".  You can optionally provide Slurm
specifications for a cluster using a resource attribute named "Slurm
specifications". The value of this attribute must conform to the Slurm
specification format and are colon separated.

Subscriptions in Coldfront map to Accounts in Slurm. The name of the Slurm
account is taken from a subscription attribute in Coldfront named "Slurm
account name". You can optionally provide Slurm specifications for the account
using a subscription attribute named "Slurm specifications". The value of this
attribute must conform to the Slurm specification format and are colon
separated.

Subscription users in Coldfront map to Users in Slurm. It is assumed all users
inherit any Slurm specifications on the account. Adding Slurm specificatins per
user is not currently supported.

## Usage

To enable this extra app add or uncomment the following in your
local\_settings.py file:

```
    EXTRA_APPS += [
        'extra.djangoapps.slurm',
    ]
```

To generate Slurm association data from Coldfront run the following command:

```
    $ python manage.py sacctmgr_dump -o tux.cfg
```

You can then load this file into Slurm with the following command:

```
    $ sacctmgr load file=tux.cfg

```
