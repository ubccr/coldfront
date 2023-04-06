# Importing Data

This howto guide demonstrates importing data into ColdFront using json files.
The examples are very basic and can be easily modified to import data from any
legacy system. 

The following sections describe how you can builk import Users, Projects,
Resources and Allocations into ColdFront. We provide an example json file
format which can be adopted to your specific needs. Exporting data from
preexisting legacy systems into this json format is left as an exercise for the
reader.

The json file format follows [Django’s serialization framework](https://docs.djangoproject.com/en/4.1/topics/serialization/) and 
can be used to import/export data from ColdFront models. For more information see the [dumpdata](https://docs.djangoproject.com/en/4.1/ref/django-admin/#dumpdata) and [loaddata](https://docs.djangoproject.com/en/4.1/ref/django-admin/#loaddata) commands.

## Importing Users

To load user data into ColdFront create a json file `users.json` in the following format:

```json
[
    {
        "fields": {
            "email": "cgray@example.com",
            "first_name": "Carl",
            "is_active": true,
            "is_staff": false,
            "is_superuser": false,
            "last_name": "Gray",
            "password": "pbkdf2_sha256$260000$hQje4tukf0uRXYwo76JZG5$SsKKuWmn4+T31ixwnmY7DRsmMsO3JpQ7PDq4U94QWQ8=",
            "username": "cgray"
        },
        "model": "auth.user"
    },
    {
        "fields": {
            "email": "sfoster@example.com",
            "first_name": "Stephanie",
            "is_active": true,
            "is_staff": false,
            "is_superuser": false,
            "last_name": "Foster",
            "password": "pbkdf2_sha256$260000$eMdXzwu1Gl9OKB9mTxpaD2$ayXIWhf5MQ3gQlL8aHyfDA+hmiA2kx5jOeIg7duh0uU=",
            "username": "sfoster"
        },
        "model": "auth.user"
    }
]
```

!!! note "Passwords optional and username must be unique"
    It is important that the username is unique. The `password` field is
    optional. Most sites use some type of external single sign on
    authentication like OAuth2 and in this case the password field can be left
    blank.

To load the json file we use the Django (ColdFront) `loaddata` command:

```coldfront loaddata --format=json users.json```


## Importing Projects

To load project data into ColdFront create a json file `projects.json` in the following format:

```json
[
    {
        "fields": {
            "description": "We want to estimate the quark chemical potential of a rotating sample of plasma.",
            "field_of_science": ["Chemistry"],
            "force_review": true,
            "pi": ["cgray"],
            "requires_review": true,
            "status": ["Active"],
            "title": "Angular momentum in QGP holography"
        },
        "model": "project.project"
    },
    {
        "fields": {
            "description": "This purpose of this project is to measure the critical behavior of quantum Hall transitions.",
            "field_of_science": ["Physics"],
            "force_review": false,
            "pi": ["sfoster"],
            "requires_review": true,
            "status": ["Active"],
            "title": "Measuring critical behavior of quantum Hall transitions"
        },
        "model": "project.project"
    }
]
```

To load the json file we use the Django (ColdFront) `loaddata` command:

```coldfront loaddata --format=json projects.json```

## Importing Resources

To load resource data into ColdFront create a json file `resources.json` in the following format:

```json
[
    {
        "fields": {
            "description": "University Academic Cluster",
            "is_allocatable": true,
            "is_available": true,
            "is_public": true,
            "name": "University HPC",
            "requires_payment": false,
            "resource_type": [
                "Cluster"
            ]
        },
        "model": "resource.resource"
    },
    {
        "fields": {
            "description": "University Research Cloud",
            "is_allocatable": true,
            "is_available": true,
            "is_public": true,
            "name": "University Cloud",
            "requires_payment": false,
            "resource_type": [
                "Cloud"
            ]
        },
        "model": "resource.resource"
    }
]
```

To load the json file we use the Django (ColdFront) `loaddata` command:

```coldfront loaddata --format=json resources.json```

## Importing Allocations

To load allocation data into ColdFront create a json file `allocations.json` in the following format:

```json
[
    {
        "fields": {
            "end_date": "2024-04-05",
            "is_changeable": true,
            "is_locked": false,
            "justification": "I need access to university cluster.",
            "project": [
                "Angular momentum in QGP holography",
                "cgray"
            ],
            "quantity": 1,
            "resources": [
                [
                    "University HPC"
                ]
            ],
            "start_date": "2023-04-06",
            "status": [
                "Active"
            ]
        },
        "model": "allocation.allocation"
    },
    {
        "fields": {
            "end_date": "2025-09-22",
            "is_changeable": true,
            "is_locked": false,
            "justification": "Need access to research cloud.",
            "project": [
                "Measuring critical behavior of quantum Hall transitions",
                "sfoster"
            ],
            "quantity": 1,
            "resources": [
                [
                    "University Cloud"
                ]
            ],
            "start_date": "2023-04-06",
            "status": [
                "Active"
            ]
        },
        "model": "allocation.allocation"
    }
]
```

To load the json file we use the Django (ColdFront) `loaddata` command:

```coldfront loaddata --format=json allocations.json```

## Importing other data

The previous sections provide examples of import specific data into ColdFront.
These examples use Django's built in [serialization framework](https://docs.djangoproject.com/en/3.2/topics/serialization/) 
which can be used to import/export any ColdFront model. One simple way to
explore this is to load the ColdFront test data and dump out the json format.
The following example assumes you've loaded the test data set using the
command: `coldfront load_test_data`. 

Here's a simple example on how to import Grants:

- Use the `dumpdata` command to figure out what the json format needs to be:

```
$ coldfront dumpdata --natural-foreign --indent=4 --format=json grant.Grant
[
{
    "model": "grant.grant",
    "pk": 1,
    "fields": {
        "created": "2023-04-06T17:01:38.438Z",
        "modified": "2023-04-06T17:01:38.438Z",
        "project": [
            "Measuring critical behavior of quantum Hall transitions",
            "sfoster"
        ],
        "title": "Quantum Halls",
        "grant_number": "12345",
        "role": "PI",
        "grant_pi_full_name": "Stephanie Foster",
        "funding_agency": [
            "Department of Defense (DoD)"
        ],
        "other_funding_agency": "",
        "other_award_number": "",
        "grant_start": "2023-04-06",
        "grant_end": "2025-09-22",
        "percent_credit": 20.0,
        "direct_funding": 200000.0,
        "total_amount_awarded": 1000000.0,
        "status": [
            "Active"
        ]
    }
}
]
```

- Create a new json file with your site specific data using the format from above:

```json
[
{
    "model": "grant.grant",
    "fields": {
        "project": [
            "Measuring critical behavior of quantum Hall transitions",
            "sfoster"
        ],
        "title": "My new Grant",
        "grant_number": "54321",
        "role": "PI",
        "grant_pi_full_name": "Stephanie Foster",
        "funding_agency": [
            "Department of Defense (DoD)"
        ],
        "grant_start": "2023-04-06",
        "grant_end": "2025-09-22",
        "direct_funding": 500000.0,
        "total_amount_awarded": 3000000.0,
        "status": [
            "Active"
        ]
    }
}
]
```

- Load the data using `loaddata` command:

```
$ coldfront loaddata --format=json grants.json
Installed 1 object(s) from 1 fixture(s)
```
