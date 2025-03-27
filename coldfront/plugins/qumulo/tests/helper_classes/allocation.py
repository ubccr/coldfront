from coldfront.plugins.qumulo.forms.AllocationForm import AllocationForm


class BaseTestableAllocationForm(AllocationForm):
    def __init__(self, *args, **kwargs):
        self.params_key = "taf_class_params"
        self.form_is_valid = None
        super().__init__(*args, **self._filter_params(**kwargs))

    def _filter_params(self, **kwargs):
        def filter_func(pair):
            key, value = pair
            if key == self.params_key:
                return False
            return True

        return dict(filter(filter_func, kwargs.items()))
