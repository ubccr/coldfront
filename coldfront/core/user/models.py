from django.contrib.auth.models import User
from django.db import models
from django.forms import ValidationError

import re


def generate_check_digit(body: str) -> str:
    total = 0
    for d in body:
        total = (total + int(d)) * 2
    
    rem = total % 11
    res = (12 - rem) % 11
    return 'X' if res == 10 else str(res)

def validate_orcid(value):
    if value is not None:
        if not isinstance(value, str):
            raise ValidationError(
                f"Invalid type: {type(value)}. Must be str.",
                code='invalid_type',
                params={"value": value})
        
        orc_groups = value.split("-")
        orc_no_hypen = ''.join(orc_groups)
        orc_body = orc_no_hypen[:-1]
        orc_check = orc_no_hypen[-1]

        if len(orc_groups) != 4:
            raise ValidationError(
                f"Invalid formatting: {value}. " +
                "Must be in form of 'XXXX-XXXX-XXXX-XXXX', where X is a digit. " +
                "Last character can be a digit or the letter X.",
                code='invalid_format',
                params={"value": value, "split_value": orc_groups}
            )
        
        for i in range(len(orc_groups) - 1):
            orc = orc_groups[i]
            if not re.match("\d{4}", orc):
                raise ValidationError(
                    f"Invalid formatting: {orc}. " +
                    "Must be in form of XXXX, where X is a digit.",
                    code='invalid_format',
                    params={"value": value, "orc_cluster": orc}
                )
        
        orc = orc_groups[-1]
        if not re.match("\d{3}(\d|X)", orc):
            raise ValidationError(
                f"Invalid formatting: {orc}. " +
                "Must be in form of XXXX, where X is a digit. " +
                "Last character can be a digit or the letter X.",
                code='invalid_format',
                params={"value": value, "orc_cluster": orc}
            )
        
        # Checksum validation
        expected_check = generate_check_digit(orc_body)
        if orc_check != expected_check:
            raise ValidationError(
                f"Checksum failure: {orc_check}. Expected {expected_check}. " +
                "The checksum is the last digit of the ORCID.",
                code='invalid_format',
                params={"value": value, "actual_check": orc_check,
                    "expected_check": expected_check}
            )

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_pi = models.BooleanField(default=False)

    # 19 = 16 digits + 3 hyphens
    orcid_id = models.CharField(max_length=19, null=True, validators=[validate_orcid])

    def save(self, *args, **kwargs):
        validate_orcid(self.orcid_id)
        super().save(*args, **kwargs)
