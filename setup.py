#!/usr/bin/env python

from setuptools import setup, find_packages
import coldfront

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='coldfront',
    version=coldfront.VERSION,
    description='HPC Resource Allocation System ',
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords='high-performance-computing resource-allocation',
    url='http://coldfront.io',
    project_urls={
        'Bug Tracker': 'https://github.com/ubccr/coldfront/issues',
        'Documentation': 'https://coldfront.readthedocs.io',
        'Source Code': 'https://github.com/ubccr/coldfront',
    },
    author='Andrew E. Bruno, Dori Sajdak, Mohammad Zia',
    license='GNU General Public License v3 (GPLv3)',
    python_requires='>=3.6',
    packages=find_packages(),
    install_requires=[
        'arrow==1.2.3',
        'bibtexparser==1.4.0',
        'blessed==1.20.0',
        'chardet==5.1.0',
        'Django==3.2.17',
        'django-crispy-forms==1.14.0',
        'Faker==11.3.0',
        'fontawesome-free==5.15.4',
        'django-environ==0.9.0',
        'django-model-utils==4.3.1',
        'django-picklefield==3.1',
        'django-q==1.3.9',
        'django-settings-export==1.2.1',
        'django-simple-history==3.2.0',
        'django-split-settings==1.2.0',
        'django-sslserver==0.22',
        'django-su==1.0.0',
        'doi2bib==0.4.0',
        'factory-boy==3.2.1',
        'future==0.18.3',
        'humanize==4.6.0',
        'idna==3.4',
        'pyparsing==3.0.9',
        'python-dateutil==2.8.2',
        'python-memcached==1.59',
        'pytz==2022.7.1',
        'redis==3.5.3',
        'requests==2.28.2',
        'six==1.16.0',
        'sqlparse==0.4.2',
        'text-unidecode==1.3',
        'urllib3==1.26.14',
        'wcwidth==0.2.6',
        'formencode==2.0.1',
    ],
    entry_points={
        'console_scripts': [
            'coldfront = coldfront:manage',
        ],
    },
    include_package_data = True,
    classifiers=[
        'Programming Language :: Python :: 3',
        'Framework :: Django :: 3.2',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Systems Administration',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ]
)
