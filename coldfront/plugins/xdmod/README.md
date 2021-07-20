# Open XDMoD integration for ColdFront

ColdFront django plugin providing Open XDMoD integration for ColdFront.  [Open
XDMoD](https://open.xdmod.org) is an open source tool to facilitate the
management of high performance computing resources and provides monitoring of
standard metrics such as utilization. This plugin syncs utilization data with
ColdFront allocation attributes and also provides a dump command to export
metadata about users to Open XDMoD.

## Design

Open XDMoD provides reporting on a rich set of metrics. Currently, this plugin
supports 2 metrics in Open XDMoD focused on reporting usage data for HPC Jobs and
Cloud core time.

The export function provides an automatable mechanism to synchronize user information
such as name and PI status from ColdFront to Open XDMoD.

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

To export user information from ColdFront to Open XDMoD:
```
    $ coldfront xdmod_dump -o /output_dir
```

You can then load this file into Open XDMoD (>= 10.0) with the following command:
```
    $ xdmod-load-json -f coldfront -i /output_dir/names.json
```
