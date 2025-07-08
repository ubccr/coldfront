# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django import forms
from django.utils.html import mark_safe


class UserSearchForm(forms.Form):
    CHOICES = [
        ("username_only", "Exact Username Only"),
        # ('all_fields', mark_safe('All Fields <a href="#" data-toggle="popover" data-trigger="focus" data-content="This option will be ignored if multiple usernames are specified."><i class="fas fa-info-circle"></i></a>')),
        (
            "all_fields",
            mark_safe(
                'All Fields <span class="text-secondary">This option will be ignored if multiple usernames are entered in the search user text area.</span>'
            ),
        ),
    ]
    q = forms.CharField(
        label="Search String",
        min_length=2,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Copy paste usernames separated by space or newline for multiple username searches!",
    )
    search_by = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect(), initial="username_only")
