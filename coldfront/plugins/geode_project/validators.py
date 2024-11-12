from django.forms import ValidationError


class ValidateAccountNumber():
    def __call__(self, value):
        if not value:
            return

        if len(value) != 9:
            raise ValidationError(f'Format is not correct', code='invalid')

        if value[2] != '-' or value[6] != '-':
            raise ValidationError(f'Format is not correct', code='invalid')
