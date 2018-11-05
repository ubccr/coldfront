# XDMoD integration for Coldfront

Coldfront django plugin providing XDMoD integration for Coldfront.  [Open
XDMoD](https://open.xdmod.org) is an open source tool to facilitate the
management of high performance computing resources and provides monitoring of
standard metrics such as utilization. This plugin syncs utilization data with
Coldfront subscription attributes.

## Design

XDMoD provides reporting on a rich set of metrics. Currently, this plugin
supports 2 metrics in XDMoD focused on reporting usage data for HPC Jobs and
Cloud core time.

## Usage

To enable this plugin add or uncomment the following in your local\_settings.py
file:

```
    EXTRA_APPS += [
        'coldfront.plugins.xdmod',
    ]
    XDMOD_API_URL = 'https://localhost'
```

## CLI Usage

To sync usage data from XDMoD to Coldfront:

```
    $ coldfront xdmod_usage -x -m cloud_core_time -v 0 -s
```
