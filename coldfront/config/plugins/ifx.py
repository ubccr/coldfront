'''
Config for ifxbilling
Installs ifxuser, ifxbilling, and author.  Sets AUTH_USER_MODEL
'''

from coldfront.config.base import INSTALLED_APPS, MIDDLEWARE

# INSTALLED_APPS = ['ifxuser'] + INSTALLED_APPS + ['author', 'ifxbilling']

MIDDLEWARE += [
    'author.middlewares.AuthorDefaultBackendMiddleware',
]

NANITE2USER_CLASS = 'coldfront.plugins.ifx.nanites.Nanite2ColdfrontUser'
