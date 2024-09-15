"""Storage of default choices for attribute and status values."""

### Allocation ###

ALLOCATION_DEFAULTS = {
    'attrtypes': (
        'Date',
        'Float',
        'Int',
        'Text',
        'Yes/No',
        'No',
        'Attribute Expanded Text'
    ),
    'statuschoices': (
        'Active',
        'Denied',
        'Expired',
        'New',
        'Paid',
        'Payment Pending',
        'Payment Requested',
        'Payment Declined',
        'Renewal Requested',
        'Revoked',
        'Unpaid',
    ),
    'changestatuschoices': ('Pending', 'Approved', 'Denied'),
    'allocationuserstatuschoices': ('Active', 'Error', 'Removed'),
    'allocationattrtypes': (
        # name, attribute_type, has_usage, is_private
        ('Cloud Account Name', 'Text', False, False),
        ('CLOUD_USAGE_NOTIFICATION', 'Yes/No', False, True),
        ('Core Usage (Hours)', 'Int', True, False),
        ('Accelerator Usage (Hours)', 'Int', True, False),
        ('Cloud Storage Quota (TB)', 'Float', True, False),
        ('EXPIRE NOTIFICATION', 'Yes/No', False, True),
        ('freeipa_group', 'Text', False, False),
        ('Is Course?', 'Yes/No', False, True),
        ('Paid', 'Float', False, False),
        ('Paid Cloud Support (Hours)', 'Float', True, True),
        ('Paid Network Support (Hours)', 'Float', True, True),
        ('Paid Storage Support (Hours)', 'Float', True, True),
        ('Purchase Order Number', 'Int', False, True),
        ('send_expiry_email_on_date', 'Date', False, True),
        ('slurm_account_name', 'Text', False, False),
        ('slurm_specs', 'Attribute Expanded Text', False, True),
        ('slurm_specs_attriblist', 'Text', False, True),
        ('slurm_user_specs', 'Attribute Expanded Text', False, True),
        ('slurm_user_specs_attriblist', 'Text', False, True),
        ('Storage Quota (GB)', 'Int', False, False),
        ('Storage_Group_Name', 'Text', False, False),
        ('SupportersQOS', 'Yes/No', False, False),
        ('SupportersQOSExpireDate', 'Date', False, False),
    ),
}


### Resource ###
RESOURCE_DEFAULTS = {
    'attrtypes': (
        'Active/Inactive',
        'Date',
        'Int',
        'Public/Private',
        'Text',
        'Yes/No',
        'Attribute Expanded Text'
    ),
    'resourceattrtypes': (
        # resource_attribute_type, attribute_type
        ('Core Count', 'Int'),
        ('expiry_time', 'Int'),
        ('fee_applies', 'Yes/No'),
        ('Node Count', 'Int'),
        ('Owner', 'Text'),
        ('quantity_default_value', 'Int'),
        ('quantity_label', 'Text'),
        ('eula', 'Text'),
        ('OnDemand','Yes/No'),
        ('ServiceEnd', 'Date'),
        ('ServiceStart', 'Date'),
        ('slurm_cluster', 'Text'),
        ('slurm_specs', 'Attribute Expanded Text'),
        ('slurm_specs_attriblist', 'Text'),
        ('Status', 'Public/Private'),
        ('Vendor', 'Text'),
        ('Model', 'Text'),
        ('SerialNumber', 'Text'),
        ('RackUnits', 'Int'),
        ('InstallDate', 'Date'),
        ('WarrantyExpirationDate', 'Date'),
    ),
    'resourcetypes': (
        # resource_type, description
        ('Cloud', 'Cloud Computing'),
        ('Cluster', 'Cluster servers'),
        ('Cluster Partition', 'Cluster Partition '),
        ('Compute Node', 'Compute Node'),
        ('Server', 'Extra servers providing various services'),
        ('Software License', 'Software license purchased by users'),
        ('Storage', 'NAS storage'),
    )
}


### Project ###

PROJECT_DEFAULTS = {
    'statuschoices': ('New', 'Active', 'Archived'),
    'projectreviewstatuschoices':  ('Completed', 'Pending'),
    'projectuserrolechoices': ('User', 'Manager'),
    'projectuserstatuschoices': (
        'Active', 'Pending - Add', 'Pending - Remove', 'Denied', 'Removed'
    ),
    # in utils.add_project_user_status_choices, projectuserstatuschoices are ['Active', 'Pending Remove', 'Denied', 'Removed'].
    # What are the correct options?
    'attrtypes': ('Date', 'Float', 'Int', 'Text', 'Yes/No'),
    'projectattrtypes': (
        # name, attribute_type, has_usage, is_private
        ('Project ID', 'Text', False, False),
        ('Account Number', 'Int', False, True),
    ),
}


### Grants ###

GRANT_DEFAULTS = {
    'fundingagencies': (
        'Department of Defense (DoD)',
        'Department of Energy (DOE)',
        'Environmental Protection Agency (EPA)',
        'National Aeronautics and Space Administration (NASA)',
        'National Institutes of Health (NIH)',
        'National Science Foundation (NSF)',
        'New York State Department of Health (DOH)',
        'New York State (NYS)',
        'Empire State Development (ESD)',
        "Empire State Development's Division of Science, Technology and Innovation (NYSTAR)",
        'Other'
    ),
    'statuschoices': ('Active', 'Archived', 'Pending')
}


### Publication ###

PUBLICATION_DEFAULTS = {
    'publicationsources': (
        # name, url
        ('doi', 'https://doi.org/'),
        ('manual', None),
    )
}
