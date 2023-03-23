from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings
RESEARCH_OUTPUT_ENABLE = import_from_settings('RESEARCH_OUTPUT_ENABLE', False)

if RESEARCH_OUTPUT_ENABLE:
    class ResearchOutputConfig(AppConfig):
        name = 'coldfront.core.research_output'
