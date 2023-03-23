from django.forms import ModelForm

from coldfront.core.research_output.models import ResearchOutput
from coldfront.core.utils.common import import_from_settings
RESEARCH_OUTPUT_ENABLE = import_from_settings('RESEARCH_OUTPUT_ENABLE', False)

if RESEARCH_OUTPUT_ENABLE:
    class ResearchOutputForm(ModelForm):
        class Meta:
            model = ResearchOutput
            exclude = ['project', ]
