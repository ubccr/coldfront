from django.core.exceptions import ValidationError


class IsAlpha:
    message = 'The entry must not contain numbers or special characters'
    code = 'invalid'

    def __init__(self, message = None) -> None:
        if message is not None:
            self.message = message

    def __call__(self, value):
        if not value.isalpha():
            raise ValidationError(self.message, self.code)
