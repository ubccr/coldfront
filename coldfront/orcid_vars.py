import orcid #NEW REQUIREMENT: orcid (pip install orcid)
from django.conf import settings
from orcid.orcid import PublicAPI

class OrcidAPI:
    '''
    Contains useful variables for ORCID
    functionalities
    '''

    ORC_CONFIG_MSG = "ORCID is not configured or is configured incorrectly. Please see local_settings.py.sample for instructions on configuring ORCID functionality."

    # String to regex ORCID id from any string
    ORC_RE_KEY = "(\d{4}-){3}\d{3}[0-9,X]"

    try:
        # Constants for orc_api (ORCID API)
        INST_KEY = settings.ORCID_INST_KEY
        INST_SECRET = settings.ORCID_INST_SECRET

        # Default ColdFront webpage. Should match one of Redirect URIs
        # in ORCID dev tools.
        ORC_REDIRECT = settings.ORCID_REDIRECT

        # Sets up orcid research info importing
        # Set sandbox to false on production
        # Requires institution key and institution secret
        orc_api = orcid.PublicAPI(INST_KEY, INST_SECRET, sandbox=settings.ORCID_USE_SANDBOX)
    except AttributeError:
        pass

    def orcid_configured() -> bool:
        '''
        Returns true if ORCID is configured and false otherwise
        '''

        try:
            settings.ORCID_INST_KEY
            settings.ORCID_INST_SECRET
            settings.ORCID_REDIRECT
            settings.ORCID_USE_SANDBOX

            PublicAPI(settings.ORCID_INST_KEY, settings.ORCID_INST_SECRET, settings.ORCID_USE_SANDBOX).get_search_token_from_orcid()

            return True
        except:
            return False
