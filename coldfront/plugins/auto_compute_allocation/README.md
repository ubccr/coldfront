# auto\_compute\_allocation - A plugin to create an automatically assigned compute allocation

Coldfront django plugin providing capability to create an automatically assigned compute allocation (a Coldfront project resource allocation mapping to an HPC Cluster resource or multiple such resources).

<b>The motivation for using this plugin is to use Coldfront as the source of truth</b>. This might be in contrast to another operating modality where information is [generally] imported from another system into Coldfront to provide allocations.

- By using the plugin an allocation to use configured HPC Cluster(s) will be created each time a new project is created, which Coldfront operators simply need to check over and then approve/activate...

This has the benefit of reducing workload:
- Coldfront operators workload is reduced slightly, whilst also providing consistency and accuracy - operators are required to input and do less.
- Another reason might be to reduce PI workload. As on a free-at-the-point of use system, its likely that all projects simply get granted a compute allocation and therefore a slurm association to be able to use the HPC Cluster(s). The PI will automatically have the allocation created by Coldfront itself.


## Design


This plugin makes use of a django signal within Coldfront's project view in order to trigger creation. Naming of the allocation created uses ``project_code``.

Allocations are named in the format _auto|Cluster|project_code_  (e.g. ``auto|Cluster|CDF0001``). This allocation description and it's delimiters within, can be controlled with the variable: ``AUTO_COMPUTE_ALLOCATION_DESCRIPTION``, though the _project_code_ will always be appended.

At the time of project creation, only the PI can be known, so this is the only user added.

Further down in the documentation, all variables are described in a table.

As well as controlling the end date of the generated allocation, the changeable and locked attributes can be toggled.

Optionally **gauges** for accelerator and core hours can be assigned to new projects by providing an integer greater than 0.

- ``AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS``
- ``AUTO_COMPUTE_ALLOCATION_CORE_HOURS``

...specifically for training (field of science = training) projects with:

- ``AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS_TRAINING``
- ``AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING``


A variable can be used to filter which Cluster resources the allocation can work with ``AUTO_COMPUTE_ALLOCATION_CLUSTERS``.

An optional usage, is to enable an **institution based fairshare attribute** - ``AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION``. This requires the _institution feature_ has been enabled correctly, such that a match is found (for the submitting PI). If a match isn't found then this attribute can't be set and the code handles.

The **slurm account can be named** and its naming controlled via ``AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT``. Similarly ``AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION_NAME_FORMAT`` gives some control over the output of the **institutional fairshare naming/value**.

**slurm_attributes can be added** with ``AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE`` and ``AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE_TRAINING``.


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


**Required Plugin load:**

| Option | Type | Default | Description |
|--- | --- | --- | --- |
| `PLUGIN_AUTO_COMPUTE_ALLOCATION` | Bool | False, not defined | Enable the plugin, required to be set as True (bool). |


Next the environment variables for the plugin itself, here are the descriptions and defaults.

### Auto_Compute_Allocation Plugin optional variables

All variables for this plugin are currently **optional**.

| Option | Type | Default | Description |
|--- | --- | --- | --- |
| `AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS` | int | 0 | Optional, **not a slurm attribute, enables guage**, number of accelerator hours to provide on the allocation, if 0 then this functionality is not triggered and no accelerator hours will be added  |
| `AUTO_COMPUTE_ALLOCATION_ACCELERATOR_HOURS_TRAINING` | int | 0 | Optional, **not a slurm attribute, enables guage**, number of accelerator hours to provide on the allocation, if 0 then this functionality is not triggered and no accelerator hours will be added. This applies to projects which select 'Training' as their field of science discipline.  |
| `AUTO_COMPUTE_ALLOCATION_CORE_HOURS` | int | 0 | Optional, **not a slurm attribute, enables guage**, number of core hours to provide on the allocation, if 0 then this functionality is not triggered and no core hours will be added  |
| `AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING` | int | 0 | Optional, **not a slurm attribute, enables guage**, number of core hours to provide on the allocation, if 0 then this functionality is not triggered and no core hours will be added. This applies to projects which select 'Training' as their field of science discipline.  |
| `AUTO_COMPUTE_ALLOCATION_END_DELTA` | int | 365 | Optional, number of days from creation of the allocation to expiry, default 365 to align with default project duration of 1 year  |
| `AUTO_COMPUTE_ALLOCATION_CHANGEABLE` | bool | True | Optional, allows the allocation to have a request logged to change - this might be useful for an extension |
| `AUTO_COMPUTE_ALLOCATION_LOCKED` | bool | False | Optional, prevents the allocation from being modified by admin - this might be useful for an extensions |
| `AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION` | bool | False | Optional, provides an institution based slurm fairshare attribute, requires that the _institution feature_ is setup correctly |
| `AUTO_COMPUTE_ALLOCATION_CLUSTERS` | tuple | empty () | Optional, filter for clusters to automatically allocate on - example value ``AUTO_COMPUTE_ALLOCATION_CLUSTERS=(Cluster1,Cluster4)`` |
| `AUTO_COMPUTE_ALLOCATION_DESCRIPTION` | str | "auto\|Cluster\|" | Optionally control the produced description for the allocation and its delimiters within. The _project_code_ will always be appended. Example resultant description: ``auto\|Cluster\|CDF0001`` |
| `AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE` | tuple | empty () | Optional, a tuple of slurm_attributes to add to the allocation. **Note each element needs an internal delimiter of a semi-colon `;` rather than a comma, if a comma is present in your intended element string**. <br><br>An example is `AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE=('GrpTRESMins=cpu=999;mem=999;gres/gpu=999',)` which defines a single element tuple and therefore 1x slurm attribute. More could be added. Note the internal semi-colon `;` delimiter instead of a comma with the string. |
| `AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE_TRAINING` | tuple | empty () | Optional, a tuple of slurm_attributes to add to the allocation for a training project. **Note each element needs an internal delimiter of a semi-colon `;` rather than a comma, if a comma is present in your intended element string**. <br><br>An example is `AUTO_COMPUTE_ALLOCATION_SLURM_ATTR_TUPLE_TRAINING=('GrpTRESMins=cpu=999;mem=999;gres/gpu=999',)` which defines a single element tuple and therefore 1x slurm attribute. More could be added. Note the internal semi-colon `;` delimiter instead of a comma with the string. |
| `AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION_NAME_FORMAT` | str | empty "" | Optional, variable to define how the fairshare attribute will be named. <br><br>**If not defined then the default format `{institution}` will be used**.|
| `AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT` | str | empty "" | Optional, variable to define how the slurm_account_name attribute will be named. <br><br>**If not defined then the default format `{project_code}_{PI_First_Initial}_{PI_Last_Name_Formatted}_{allocation_id}` will be used**. <br><br> If you just want `project_code` then use `AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT="{project_code}"`.| 


#### AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT - detail

This table shows the possible values that can be used for the ENV var ``AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT`` string.

| AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT | value | comment |
|--- | --- | --- |
| | `allocation_id` | the allocation id - useful as will be a distinct number (pk) - this will not necessarily be in sequence but is unique |
| | `institution_abbr_upper_lower` | the institution's capital letters extracted and joined as lowercase - to make an abbreviation |
| | `institution_abbr_upper_upper` | the institution's capital letters extracted and joined as uppercase - to make an abbreviation |
| | `institution` | institution with spaces converted to '_' |
| | `institution_formatted` | institution lowercase with spaces converted to '_' |
| | `PI_first_initial` | PI last name initial lowercase|
| | `PI_first_name` | PI first name lowercase |
| | `PI_last_initial` | PI first initial lowercase |
| | `PI_last_name_formatted` | PI last name lowercase with spaces converted to '_' |
| | `PI_last_name` | PI last name lowercase |
| | `project_code` | the project_code |
| | `project_id` | the project_id (pk) wont be distinct within multiple allocations in the same project |


#### AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION_NAME_FORMAT - detail

This table shows the possible values that can be used for the ENV var ``AUTO_COMPUTE_ALLOCATION_FAIRSHARE_INSTITUTION_NAME_FORMAT`` string.

| AUTO_COMPUTE_ALLOCATION_SLURM_ACCOUNT_NAME_FORMAT | value | comment |
|--- | --- | --- |
| | `institution_abbr_upper_lower` | the institution's capital letters extracted and joined as lowercase - to make an abbreviation |
| | `institution_abbr_upper_upper` | the institution's capital letters extracted and joined as uppercase - to make an abbreviation |
| | `institution` | institution with spaces converted to '_' |
| | `institution_formatted` | institution lowercase with spaces converted to '_' |



## Example settings

- show a gauge for 10k core hours for new project
- show a gauge for 100 core hours for a new training project
- default 365 end delta - no need to set variable

```
AUTO_COMPUTE_ALLOCATION_CORE_HOURS=10000
AUTO_COMPUTE_ALLOCATION_CORE_HOURS_TRAINING=100
```


## Future work

Future work could include:

- slurm parent accounts
- a seperate plugin for storage allocations - ``auto_storage_allocation``
