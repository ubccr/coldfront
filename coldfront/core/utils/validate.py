import datetime
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
import formencode
from formencode import validators, Invalid

class AttributeValidator:

    def __init__(self, value):
        self.value = value

    def validate_int(self):
        try:
            validate = validators.Int()
            validate.to_python(self.value)
        except:
            raise ValidationError(
                f'Invalid Value {self.value}. Value must be an int.') 

    def validate_float(self):
        try:
            validate = validators.Number()
            validate.to_python(self.value)
        except:
            raise ValidationError(
                f'Invalid Value {self.value}. Value must be an float.') 

    def validate_yes_no(self):
        try:
            validate = validators.OneOf(['Yes','No'])
            validate.to_python(self.value)
        except:
            raise ValidationError(
                f'Invalid Value {self.value}. Value must be an Yes/No value.') 

    def validate_date(self):
        try:
            datetime.datetime.strptime(self.value.strip(), "%Y-%m-%d")
        except:
            raise ValidationError(
                f'Invalid Value {self.value}. Date must be in format YYYY-MM-DD and date must be today or later.')