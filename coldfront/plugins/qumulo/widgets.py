from django.forms.widgets import Widget, ChoiceWidget


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


class FilterableCheckBoxTableInput(ChoiceWidget):
    template_name = "filterable_checkbox_table_input.html"
    columns = []
    allow_multiple_selected = True

    def init(self, initial_filter=None):
        self.initial_filter = initial_filter

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        context["widget"]["options"] = list(
            map(lambda element: element[1][0], context["widget"]["optgroups"])
        )
        context["widget"]["columns"] = self.columns
        context["widget"]["initial_filter"] = self.initial_filter

        return context

    class Media:
        js = ("filterable_checkbox_table_input.js",)
