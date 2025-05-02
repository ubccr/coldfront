# auto\_compute\_allocation - A plugin to create an automatically assigned compute allocation

Coldfront django plugin providing capability to create an automatically assigned compute allocation.

This plugin makes use of a django signal within Coldfront's project view in order trigger creation. Naming of the allocation created uses ``project_code``.

Allocations are named in the format _auto:Cluster:project_code_  (e.g. ``auto:Cluster:CDF0001``)

At the time of creation, only the PI can be known, so this is the only user added.

Further down in the documentation, all variables are described in a table.

As well as controlling the end date of the generated allocation, the changeable and locked attributes can be toggled.

Optionally core hours can be assigned to new projects with ``AUTO_COMPUTE_ALLOCATION_CORE_HOURS`` and specifically training projects with ``AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING``. These are activated by providing an integer greater than 0.

Finally an optional usage, is to enable an institute based fairshare attribute. This requires the variable ``PROJECT_INSTITUTION_EMAIL_MAP`` has been defined such that matches are found.

Currently any Cluster resources found are assigned to the allocation. A future feature might be to filter this.

## Requirements

The plugin requires that the project code feature is enabled.

``PROJECT_CODE`` is required to be set to a valid string. E.g. 'CDF', 'COMP' etc. in the Coldfront django settings - e.g. coldfront.env


## Usage

The plugin requires that various environment variables are defined in the Coldfront django settings - e.g. coldfront.env

Example pre-requisites - we require ``PROJECT_CODE`` to be enabled, here is an example using CDF and padding of 4. The padding is optional but ``PROJECT_CODE`` is required.

**Example Required project_code:**
```
PROJECT_CODE="CDF"
```
Example Optional project_code padding:
```
PROJECT_CODE_PADDING=4
```


Next the environment variables for the plugin itself, here are the descriptions and defaults.

### Auto_Compute_Allocation Plugin optional variables

All variables for this plugin are currently **optional**.

| Option | Default | Description |
|--- | --- | --- |
| `AUTO_COMPUTE_ALLOCATION_CORE_HOURS` | `int`, 0 | Optional, number of core hours to provide on the allocation, if 0 then this functionality is not triggered and no core hours will be added  |
| `AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING` | `int`, 0 | Optional, number of core hours to provide on the allocation, if 0 then this functionality is not triggered and no core hours will be added. This applies to projects which select 'Training' as their field of science discipline.  |
| `AUTO_COMPUTE_ALLOCATION_END_DELTA` | `int`, 365 | Optional, number of days from creation of the allocation to expiry, default 365 to align with default project duration of 1 year  |
| `AUTO_COMPUTE_ALLOCATION_CHANGABLE` | `bool`, True | Optional, allows the allocation to have a request logged to change - this might be useful for an extension |
| `AUTO_COMPUTE_ALLOCATION_LOCKED` | `bool`, False | Optional, prevents the allocation from being modified by admin - this might be useful for an extensions |
| `AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION` | `bool`, False | Optional, provides an institution based slurm fairshare attribute, requires that `PROJECT_INSTITUTION_EMAIL_MAP` is set |
| `AUTO_COMPUTE_ALLOCATION_CLUSTERS` | `tuple`, empty () | Optional, filter for clusters to automatically allocate on - example value ``AUTO_COMPUTE_ALLOCATION_CLUSTERS=(Cluster1,Cluster4)`` |



## Example settings

- 10k core hours for new project
- 100 core hours for training project
- default 365 end delta - no need to set variable

```
AUTO_COMPUTE_ALLOCATION_CORE_HOURS=10000
AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING=100
```


## Future work

Future work could include:

- accelerator allocation
- some more specific logic to map to partitions
