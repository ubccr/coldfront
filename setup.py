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
        'arrow==1.2.1',
        'bibtexparser==1.2.0',
        'blessed==1.19.0',
        'chardet==4.0.0',
        'Django==3.2.14',
        'django-crispy-forms==1.13.0',
        'django-environ==0.8.1',
        'django-model-utils==4.2.0',
        'django-picklefield==3.0.1',
        'django-q==1.3.9',
        'django-settings-export==1.2.1',
        'django-simple-history==3.0.0',
        'django-split-settings==1.1.0',
        'django-sslserver==0.22',
        'django-su==0.9.0',
        'doi2bib==0.4.0',
        'future==0.18.2',
        'humanize==3.13.1',
        'idna==3.3',
        'pyparsing==3.0.6',
        'python-dateutil==2.8.2',
        'python-memcached==1.59',
        'pytz==2021.3',
        'redis==3.5.3',
        'requests==2.27.1',
        'six==1.16.0',
        'urllib3==1.26.8',
        'wcwidth==0.2.5',
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
