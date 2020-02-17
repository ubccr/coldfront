import re


class SnakeCaseTemplateNameMixin:
    # by default:
    # Django converts the model class name to simply lowercase (i.e. not snake_case)
    # however, we use snake_case filename style throughout coldfront
    #
    # thus, for consistency:
    # override get_template_names() to use snake_case instead of simply lowercase

    def get_template_names(self):
        def to_snake(string):
            # note that this is an oversimplified implementation
            # it should work in the majority of cases, even allowing us to change app/class/etc. names
            # but cases like DOIDisplay (or similar, using multiple caps in a row) would fail

            return string[0].lower() + re.sub('([A-Z])', r'_\1', string[1:]).lower()

        app_label = self.model._meta.app_label
        model_name = self.model.__name__

        return ['{}/{}{}.html'.format(app_label, to_snake(model_name), self.template_name_suffix)]
