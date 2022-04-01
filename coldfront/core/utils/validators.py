from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class IsAlpha:
    message = 'The entry must not contain numbers or special characters'
    code = 'invalid'

    def __init__(self, message = None) -> None:
        if message is not None:
            self.message = message

    def __call__(self, value):
        if not value.isalpha():
            raise ValidationError(self.message, self.code)

    def __eq__(self, other):
        return (
            isinstance(other, IsAlpha)
            and (self.message == other.message)
        )
