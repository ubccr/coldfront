# Storage Plugin for ColdFront

The storage plugin allows to dump the Storage Allocations info (Storage Quota (GB), Storage_Group_Name, Status) to a file or standard output.

## Configuration


The plugin checks for Allocations with   `Storage Quota (GB)`  or  `Storage Quota (TB)` and `Storage_Group_Name`.
If are defined, it exports them to a file in the format
`Storage Name|Storage_Group_Name|gigabytes|Status`

Example:

    root@localhost:/opt# coldfront storage_dump
    Found 2 allocations.
    Processing allocation ID: 2
    Attributes for allocation 2: {'Storage_Group_Name': 'project_a', 'Storage Quota (GB)': '4000'}
    Prepared quota: 4000.0 GB for storage group: project_a, Status: Denied
    Processing allocation ID: 3
    Attributes for allocation 3: {}
    Beegfs Fast Storage|project_a|4000|Denied


To save the output as a file use `-o output.txt` or `--output_file output.txt`
