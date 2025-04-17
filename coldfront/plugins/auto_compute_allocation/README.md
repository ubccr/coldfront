# auto\_compute\_allocation - A plugin to create an automatically assigned compute allocation

Coldfront django plugin providing capability to create an automatically assigned compute allocation.

This plugin makes use of a django signal within Coldfront's project view in order trigger creation. Naming of the allocation created uses project\_code.

As well as controlling the end date of the generated allocation, the changeable and locked attributes can be toggled.

Finally an optional usage, is to enable an institute based fairshare attribute.

Currently any Cluster resources found are assigned to the allocation. A future feature might be to filter this.

## Requirements

The plugin requires that the project code feature is enabled.

PROJECT\_CODE is required to be set to a valid string. E.g. 'CDF', 'COMP' etc. in the Coldfront django settings - e.g. coldfront.env


## Usage

The plugin requires that various environment variables are defined in the Coldfront django settings - e.g. coldfront.env

Example pre-requisites - we require `project_code` to be enabled, here is an example using CDF and padding of 4.

**Example Required:**
```
PROJECT_CODE="CDF"
PROJECT_CODE_PADDING=4
```

Next the environment variables for the plugin itself, here are the descriptions and defaults:

**Optional**:

All variables for this plugin are currently optional.

| Option | Default | Description |
|--- | --- | --- |
| `AUTO_COMPUTE_ALLOCATION_END_DELTA` | `int`, 365 | Optional, number of days from creation of the allocation to expiry, default 365 to align with default project duration of 1 year  |
| `AUTO_COMPUTE_ALLOCATION_CHANGABLE` | `bool`, True | Optional, allows the allocation to have a request logged to change - this might be useful for an extension |
| `AUTO_COMPUTE_ALLOCATION_LOCKED` | `bool`, False | Optional, prevents the allocation from being modified by admin - this might be useful for an extensions |
| `AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION` | `bool`, False | Optional, provides an institution based slurm fairshare attribute, requires that `PROJECT_INSTITUTION_EMAIL_MAP` is set |
