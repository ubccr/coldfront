# Open XDMoD integration for ColdFront

ColdFront django plugin providing Open XDMoD integration for ColdFront.  [Open
XDMoD](https://open.xdmod.org) is an open source tool to facilitate the
management of high performance computing resources and provides monitoring of
standard metrics such as utilization. This plugin syncs utilization data with
ColdFront allocation attributes.

## Design

Open XDMoD provides reporting on a rich set of metrics. Currently, this plugin
supports 2 metrics in Open XDMoD focused on reporting usage data for HPC Jobs and
Cloud core time.


## Setup

In order to use this plugin, you will need to (within Coldfront's django admin):

- Create a Resource Attribute Type
- Add this new Resource Attribute Type to your cluster resource (slurm cluster resource)

You may also need to check your xdmod instance's resources.json has ``"pi_column": "account_name"`` as per xdmod documentation.

### Coldfront django admin steps

#### Create the new Resourece Attribute type

```
Resource Attribute Type: xdmod_resource
Attribute type name: text
```

#### Edit the existing Resource (slurm cluster)

```
Resource attribute type: xdmod_resource
Value: slurm_cluster_as_named_in_slurm
```

## Usage

To enable this plugin set the following environment variables:

```
PLUGIN_XDMOD=True
XDMOD_API_URL='https://localhost'
```

## CLI Usage

To sync usage data from XDMoD to ColdFront:

```
    $ coldfront xdmod_usage -x -m cloud_core_time -v 0 -s
```
