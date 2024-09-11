from django.forms import Widget
import logging

logger = logging.getLogger(__name__)


class MultiSelectLookupInput(Widget):
    template_name = "multi_select_lookup_input.html"

    class Media:
        js = ("multi_select_lookup_input.js",)

    def value_from_datadict(self, data, files, name):
        try:
            getter = data.getlist
        except AttributeError:
            getter = data.get

        getter_return = getter(name)

        raw_string = (
            getter_return[0]
            if hasattr(getter_return, "__getitem__") and len(getter_return) > 0
            else ""
        )

        return raw_string.split(",")
