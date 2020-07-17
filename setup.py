#!/usr/bin/env python

from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='coldfront',
    version='1.0.1',
    description='HPC Resource Allocation System ',
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords='high-performance-computing resource-allocation',
    url='http://coldfront.io',
    project_urls={
        'Bug Tracker': 'https://github.com/ubccr/coldfront/issues',
        'Documentation': 'https://ubccr.github.io/coldfront-docs/',
        'Source Code': 'https://github.com/ubccr/coldfront',
    },
    author='Andrew E. Bruno, Dori Sajdak, Mohammad Zia',
    license='GNU General Public License v3 (GPLv3)',
    packages=find_packages(),
    install_requires=[
        'arrow==0.13.1',
        'bibtexparser==1.1.0',
        'blessed==1.15.0',
        'chardet==3.0.4',
        'Django==2.2.13',
        'django-crispy-forms==1.7.2',
        'django-model-utils==3.1.2',
        'django-picklefield==2.0',
        'django-q==1.0.1',
        'django-settings-export==1.2.1',
        'django-simple-history==2.7.2',
        'django-sslserver==0.20',
        'django-su==0.8.0',
        'doi2bib==0.3.0',
        'future==0.17.1',
        'humanize==0.5.1',
        'idna==2.8',
        'pyparsing==2.3.1',
        'python-dateutil==2.8.0',
        'python-memcached==1.59',
        'pytz==2018.9',
        'redis==3.2.1',
        'requests==2.22.0',
        'six==1.12.0',
        'urllib3==1.24.2',
        'wcwidth==0.1.7',
    ],
    entry_points={
        'console_scripts': [
            'coldfront = coldfront:manage',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Framework :: Django :: 2.2',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Systems Administration',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ]
)
