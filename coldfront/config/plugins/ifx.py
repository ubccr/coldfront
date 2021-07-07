'''
Config for ifxbilling
Installs ifxuser, ifxbilling, and author.  Sets AUTH_USER_MODEL
'''
import os
from coldfront.config.base import INSTALLED_APPS, MIDDLEWARE

INSTALLED_APPS = ['ifxuser'] + INSTALLED_APPS + ['author', 'ifxbilling', 'rest_framework.authtoken',]

MIDDLEWARE += [
    'author.middlewares.AuthorDefaultBackendMiddleware',
]

NANITE2USER_CLASS = 'coldfront.plugins.ifx.nanites.Nanite2ColdfrontUser'

IFX_APP = {
    'name': 'coldfront',
    'token': os.environ.get('COLDFRONT_IFX_APP_TOKEN', 'aslkdfj'),
}

class FACILITY():
    NAME = 'Research Computing Storage'
    OBJECT_CODE = '6803'
