# auto\_compute\_allocation - A plugin to create an automatically assigned compute allocation

Coldfront django plugin providing capability to create an automatically assigned compute allocation (a coldfront project resource allocation mapping to an HPC Cluster resource or multiple such resources).

The motivation for using this plugin is to use Coldfront as the source of truth. This might be in contrast to another operating modality where information is [generally] imported from another system into Coldfront to provide allocations.

- By using the plugin an allocation to use configured HPC Cluster(s) will be created each time a new project is created, which Coldfront operators simply need to check over and then approve/activate...

This has the benefit of reducing Workload:
- Coldfront operators workload is reduced slightly, whilst also providing consistency and accuracy - operators are required to input and do less.
- Another reason might be to reduce PI workload. As on a free-at-the-point of use system, its likely that all projects simply get granted a compute allocation and therefore a slurm association to be able to use the HPC Cluster(s). The PI will automatically have the allocation created by Coldfront itself.


## Design


This plugin makes use of a django signal within Coldfront's project view in order to trigger creation. Naming of the allocation created uses ``project_code``.

Allocations are named in the format _auto|Cluster|project_code_  (e.g. ``auto|Cluster|CDF0001``). This allocation description and it's delimiters within, can be controlled with the variable: ``AUTO_COMPUTE_ALLOCATION_DESCRIPTION``, though the _project_code_ will always be appended.

At the time of project creation, only the PI can be known, so this is the only user added.

Further down in the documentation, all variables are described in a table.

As well as controlling the end date of the generated allocation, the changeable and locked attributes can be toggled.

Optionally core hours can be assigned to new projects with ``AUTO_COMPUTE_ALLOCATION_CORE_HOURS`` and specifically training projects with ``AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING``. These are activated by providing an integer greater than 0.

A variable can be used to filter which Cluster resources the allocation can work with ``AUTO_COMPUTE_ALLOCATION_CLUSTERS``.

Finally an optional usage, is to enable an institute based fairshare attribute. This requires the _institution feature_ has been enabled correctly, such that a match is found (for the submitting PI). If a match isn't found then this attribute can't be set and the code handles.


### Design - signals and actions

#### signals

The following Coldfront django signal is used by this plugin, upon Coldfront WebUI action:

- project new

#### actions

The aforementioned signal triggers a function in ``tasks.py``, this in turn uses functions in ``utils.py`` to accomplish the action required which is to create an automatically generated compute allocation for the project.

## Management commands

No management commands are present or required by this plugin itself.


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
| `AUTO_COMPUTE_ALLOCATION_CHANGEABLE` | `bool`, True | Optional, allows the allocation to have a request logged to change - this might be useful for an extension |
| `AUTO_COMPUTE_ALLOCATION_LOCKED` | `bool`, False | Optional, prevents the allocation from being modified by admin - this might be useful for an extensions |
| `AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION` | `bool`, False | Optional, provides an institution based slurm fairshare attribute, requires that the _institution feature_ is setup correctly |
| `AUTO_COMPUTE_ALLOCATION_CLUSTERS` | `tuple`, empty () | Optional, filter for clusters to automatically allocate on - example value ``AUTO_COMPUTE_ALLOCATION_CLUSTERS=(Cluster1,Cluster4)`` |
| ``AUTO_COMPUTE_ALLOCATION_DESCRIPTION`` | `str`, "auto\|Cluster\|" | Optionally control the produced description for the allocation and its delimiters within. The _project_code_ will always be appended. Example resultant description: ``auto\|Cluster\|CDF0001`` |



## Example settings

- 10k core hours for new project
- 100 core hours for a new training project
- default 365 end delta - no need to set variable

```
AUTO_COMPUTE_ALLOCATION_CORE_HOURS=10000
AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING=100
```


## Future work

Future work could include:

- accelerator allocation
- some more specific logic to map to partitions
