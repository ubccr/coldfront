import datetime
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
import formencode
from formencode import validators, Invalid
import magic

class AttributeValidator:

    def __init__(self, value, doc):
        self.value = value
        self.doc = doc

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
        
    def validate_doc(self):
        # try:
        if self.doc:
            if self.doc.size > 10485760 :
                raise ValidationError("This document exceeds size limits")
            content_mime_type = magic.Magic(mime=True)
            # file_type = content_mime_type.from_buffer(self.doc.read())
            if content_mime_type.from_buffer(self.doc.read()) != "application/pdf":
                raise ValidationError("Invalid file type")
            self.doc.seek(0)
