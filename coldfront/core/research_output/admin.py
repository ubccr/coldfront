from django.contrib import admin
from coldfront.core.utils.common import import_from_settings
from simple_history.admin import SimpleHistoryAdmin

from coldfront.core.research_output.models import ResearchOutput

# ! FIGURE OUT HOW TO HIDE IN ADMIN
# todos: admin

_research_output_fields_for_end = ['created_by', 'project', 'created', 'modified']

RESEARCH_OUTPUT_ENABLE = import_from_settings('RESEARCH_OUTPUT_ENABLE', False)

if RESEARCH_OUTPUT_ENABLE:
    @admin.register(ResearchOutput)
    class ResearchOutputAdmin(SimpleHistoryAdmin):
        list_display = [
            field.name for field in ResearchOutput._meta.get_fields()
            if field.name not in _research_output_fields_for_end
        ] + _research_output_fields_for_end
        list_filter = (
            'project',
            'created_by',
        )
        ordering = (
            'project',
            '-created',
        )

        # display the noneditable fields on the "change" form
        readonly_fields = [
            field.name for field in ResearchOutput._meta.get_fields()
            if not field.editable
        ]

        # the view implements some Add logic that we need not replicate here
        # to simplify: remove ability to add via admin interface
        def has_add_permission(self, request):
            return False
